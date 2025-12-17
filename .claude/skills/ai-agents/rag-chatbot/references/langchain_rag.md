# LangChain RAG Patterns

## Document Loaders

### PDF Loading
```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("document.pdf")
docs = loader.load()  # Returns list of Document objects
```

### Web Page Loading
```python
from langchain_community.document_loaders import WebBaseLoader
import bs4

loader = WebBaseLoader(
    web_paths=["https://example.com/page"],
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(class_=("article", "content"))
    )
)
docs = loader.load()
```

### Text File Loading
```python
from langchain_community.document_loaders import TextLoader

loader = TextLoader("document.txt", encoding="utf-8")
docs = loader.load()
```

### Directory Loading
```python
from langchain_community.document_loaders import DirectoryLoader

loader = DirectoryLoader(
    "./documents",
    glob="**/*.pdf",
    loader_cls=PyPDFLoader
)
docs = loader.load()
```

## Text Splitting

### RecursiveCharacterTextSplitter (Recommended)
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " ", ""]
)
chunks = splitter.split_documents(docs)
```

### Markdown Splitting
```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]
splitter = MarkdownHeaderTextSplitter(headers_to_split_on)
chunks = splitter.split_text(markdown_text)
```

## Gemini Embeddings

### Basic Setup
```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.environ["GOOGLE_API_KEY"]
)
# Output dimension: 768
```

### Embedding Operations
```python
# Single query
query_vector = embeddings.embed_query("What is machine learning?")

# Multiple documents
doc_vectors = embeddings.embed_documents([
    "Document 1 content",
    "Document 2 content"
])
```

## Retrieval Tool Creation

### Basic Tool with @tool Decorator
```python
from langchain.tools import tool

@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Retrieve information to answer a query."""
    docs = vector_store.similarity_search(query, k=4)
    serialized = "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}"
        for doc in docs
    )
    return serialized, docs
```

### Advanced Retrieval with Parameters
```python
from typing import Literal

@tool
def retrieve_with_filter(
    query: str,
    section: Literal["introduction", "methods", "results"]
):
    """Retrieve from specific document section."""
    docs = vector_store.similarity_search(
        query,
        k=4,
        filter={"section": section}
    )
    return "\n\n".join(doc.page_content for doc in docs)
```

## Vector Store Operations

### Similarity Search
```python
# Basic search
results = vector_store.similarity_search(query, k=4)

# Search with scores
results = vector_store.similarity_search_with_score(query, k=4)
for doc, score in results:
    print(f"Score: {score:.4f} - {doc.page_content[:50]}")

# Search by vector
embedding = embeddings.embed_query(query)
results = vector_store.similarity_search_by_vector(embedding, k=4)
```

### Metadata Filtering
```python
# Filter by metadata
results = vector_store.similarity_search(
    query,
    k=4,
    filter={"source": "technical_docs"}
)
```

## RAG Chain Patterns

### Simple RAG Chain
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

template = """Answer based on context:

Context: {context}

Question: {question}

Answer:"""

prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

answer = chain.invoke("What is the main topic?")
```
