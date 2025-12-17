#!/usr/bin/env python3
"""
RAG Chatbot with LangGraph and Supabase.

A conversational AI that retrieves relevant documents from Supabase
and generates contextual responses using Gemini.

Usage:
    python rag_chatbot.py

Environment variables:
    SUPABASE_URL: Your Supabase project URL
    SUPABASE_KEY: Your Supabase anon key
    GOOGLE_API_KEY: Your Google API key for Gemini
"""

import os
from typing import Annotated, Optional
from operator import add
from pydantic import BaseModel, Field
from supabase import create_client
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessage(BaseModel):
    """Schema for a chat message."""
    role: str
    content: str


class ChatResponse(BaseModel):
    """Schema for chatbot response."""
    answer: str
    sources: list[str] = Field(default_factory=list)
    thread_id: str


class RetrievedDocument(BaseModel):
    """Schema for retrieved document."""
    id: int
    content: str
    metadata: dict
    similarity: float


# ============================================================================
# State Definition
# ============================================================================

class RAGState(MessagesState):
    """State for RAG chatbot graph."""
    context: Annotated[list[str], add]
    sources: Annotated[list[str], add]


# ============================================================================
# Clients
# ============================================================================

def get_embeddings():
    """Initialize Gemini embeddings."""
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.environ.get("GOOGLE_API_KEY")
    )


def get_llm():
    """Initialize Gemini chat model."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
        temperature=0.7
    )


def get_supabase():
    """Initialize Supabase client."""
    return create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_KEY")
    )


# ============================================================================
# Graph Nodes
# ============================================================================

# Initialize clients (module level for reuse)
embeddings = None
llm = None
supabase = None


def init_clients():
    """Initialize all clients."""
    global embeddings, llm, supabase
    embeddings = get_embeddings()
    llm = get_llm()
    supabase = get_supabase()


def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents from Supabase."""
    # Get the last user message
    last_message = state["messages"][-1]
    query = last_message.content if hasattr(last_message, "content") else str(last_message)

    # Generate embedding for query
    query_embedding = embeddings.embed_query(query)

    # Search Supabase
    result = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "match_count": 4,
            "match_threshold": 0.5
        }
    ).execute()

    # Extract context and sources
    context = []
    sources = []

    for doc in result.data:
        context.append(doc["content"])
        source = doc.get("metadata", {}).get("source", f"Document {doc['id']}")
        if source not in sources:
            sources.append(source)

    return {"context": context, "sources": sources}


def generate_node(state: RAGState) -> dict:
    """Generate response using retrieved context."""
    # Build context string
    context_str = "\n\n---\n\n".join(state.get("context", []))

    # Get conversation history
    messages = state["messages"]

    # Build system prompt with context
    system_prompt = f"""You are a helpful assistant that answers questions based on the provided context.
Always ground your answers in the context provided. If the context doesn't contain
relevant information, say so and provide what help you can.

Context:
{context_str}

Instructions:
- Answer based on the context above
- Be concise but thorough
- If unsure, acknowledge uncertainty
- Cite relevant parts of the context when appropriate"""

    # Prepare messages for LLM
    llm_messages = [SystemMessage(content=system_prompt)]

    # Add conversation history (last few messages)
    for msg in messages[-5:]:
        if hasattr(msg, "content"):
            if hasattr(msg, "type"):
                if msg.type == "human":
                    llm_messages.append(HumanMessage(content=msg.content))
                elif msg.type == "ai":
                    llm_messages.append(AIMessage(content=msg.content))
            else:
                llm_messages.append(HumanMessage(content=msg.content))

    # Generate response
    response = llm.invoke(llm_messages)

    return {"messages": [AIMessage(content=response.content)]}


# ============================================================================
# Graph Builder
# ============================================================================

def build_graph(checkpointer=None):
    """Build the RAG chatbot graph."""
    # Initialize clients
    init_clients()

    # Build graph
    builder = StateGraph(RAGState)

    # Add nodes
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)

    # Add edges
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    # Compile with checkpointer
    return builder.compile(checkpointer=checkpointer)


# ============================================================================
# Chat Interface
# ============================================================================

class RAGChatbot:
    """RAG Chatbot with conversation memory."""

    def __init__(self, thread_id: Optional[str] = None):
        self.checkpointer = InMemorySaver()
        self.graph = build_graph(self.checkpointer)
        self.thread_id = thread_id or "default"

    def chat(self, message: str) -> ChatResponse:
        """Send a message and get a response."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config
        )

        # Get the last AI message
        ai_message = result["messages"][-1]
        sources = result.get("sources", [])

        return ChatResponse(
            answer=ai_message.content,
            sources=sources,
            thread_id=self.thread_id
        )

    def stream_chat(self, message: str):
        """Stream a response token by token."""
        config = {"configurable": {"thread_id": self.thread_id}}

        for event in self.graph.stream(
            {"messages": [HumanMessage(content=message)]},
            config,
            stream_mode="values"
        ):
            if event.get("messages"):
                last_msg = event["messages"][-1]
                if hasattr(last_msg, "content"):
                    yield last_msg.content

    def get_history(self) -> list[ChatMessage]:
        """Get conversation history."""
        config = {"configurable": {"thread_id": self.thread_id}}
        state = self.graph.get_state(config)

        history = []
        for msg in state.values.get("messages", []):
            if hasattr(msg, "type") and hasattr(msg, "content"):
                history.append(ChatMessage(
                    role=msg.type,
                    content=msg.content
                ))

        return history

    def clear_history(self):
        """Clear conversation history by starting a new thread."""
        import uuid
        self.thread_id = str(uuid.uuid4())


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Interactive CLI for RAG chatbot."""
    print("RAG Chatbot initialized. Type 'quit' to exit, 'clear' to reset.\n")

    chatbot = RAGChatbot()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Goodbye!")
                break

            if user_input.lower() == "clear":
                chatbot.clear_history()
                print("Conversation cleared.\n")
                continue

            # Get response
            response = chatbot.chat(user_input)

            print(f"\nAssistant: {response.answer}")

            if response.sources:
                print(f"\nSources: {', '.join(response.sources)}")

            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
