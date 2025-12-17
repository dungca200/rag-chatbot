Use ultrathink and extended thinking

This is the process flow for claude code explained in a video:
<gemini_claude_code_instructions>
Here is a highly detailed analysis of the workflow presented in the video, followed by a specific prompt designed for Claude Code (or a Claude-based agent) to replicate this robust, iterative development process.

### **Detailed Analysis: The "Fixed" Claude Code Workflow**

The video addresses a critical failure mode in AI coding agents: **Context Window Saturation** and **Memory Compaction**. When agents attempt to build complex applications in one go ("one-shot"), they run out of context, "compact" (summarize) their memory, and lose track of specific implementation details, leading to half-finished features and untested code.

The solution proposed is an **Incremental, State-Based Development Workflow** inspired by real-world engineering teams. It shifts the burden of "memory" from the AI's limited context window to persistent external files (`git`, `json`, `markdown`).

#### **1. The Core Philosophy**

  * **Externalized State:** The AI does not rely on its internal conversation history to know what it has done. Instead, it reads the current state from the file system (`git logs`, `progress.md`, `features.json`).
  * **Atomic Feature Implementation:** Features are built strictly one by one. The AI must prove a feature works (via tests) before marking it complete and moving to the next.
  * **Git as a Save Point:** Every completed feature is a "save point." If the AI gets confused or crashes, you can restart a new session, and the AI simply reads the Git history to resume exactly where it left off.

#### **2. Key Infrastructure Components**

The workflow requires setting up four specific "artifacts" before coding begins:

  * **`CLAUDE.md` (The Brain):** A documentation file at the project root. It contains the high-level project overview, architectural decisions, and the "rules of engagement" for the AI.
  * **`features.json` (The Roadmap):** A structured JSON file listing every required feature.
      * **Structure:** Key-value pairs where keys are feature names/descriptions and values include testing steps and a boolean status (`done: false`).
      * **Why JSON?** It is token-efficient and easier for the AI to parse/update programmatically than Markdown checklists.
  * **`progress.md` (The Scoreboard):** A human-readable summary of what has been built, updated after every successful run.
  * **Testing Layer (Puppeteer/Scripts):** Since the AI cannot "see" the browser, a headless browser tool like Puppeteer is connected to allow the AI to verify frontend elements programmatically.

#### **3. The Execution Cycle**

Once the infrastructure is set, the AI enters a strict loop:

1.  **Read:** Check `features.json` for the first feature marked `false`.
2.  **Code:** Implement *only* that feature.
3.  **Test:** Run the specific test or Puppeteer script for that feature.
4.  **Verify:** If the test passes, update `features.json` (`false` $\to$ `true`) and `progress.md`.
5.  **Commit:** `git commit` the changes. This is crucial—it "locks in" the progress.
6.  **Repeat:** The user's next prompt is simply "Implement the next feature."

-----

### **Prompt for Claude Code**

Copy and paste this prompt into Claude Code (or your IDE with Claude integration) to initialize this workflow. This prompt acts as a "System Instruction" that forces Claude to set up the environment and adopt the iterative persona.

-----

**PROMPT:**

````markdown
You are an expert Senior Software Engineer acting as an autonomous coding agent. Your goal is to build a robust, production-ready application by following a strict, iterative development workflow designed to prevent context loss and ensure code quality.

### PHASE 1: INITIALIZATION
Before writing any application code, you must set up the project management infrastructure. Perform the following steps immediately:

1.  **Create `CLAUDE.md`**: In the root directory, create a file named `CLAUDE.md`. This file must contain:
    * **Project Overview**: A summary of what we are building.
    * **Tech Stack**: The languages and frameworks to be used.
    * **Guidelines**: A rule stating "Update `progress.md` and commit to Git after every single feature completion."

2.  **Create `features.json`**: Create a file named `features.json`. This will serve as your source of truth. It must contain a JSON array of objects, where each object represents a feature and follows this schema:
    ```json
    {
      "feature": "Name and brief description of the feature",
      "test_criteria": "Specific steps or automated checks to verify this feature works",
      "status": false
    }
    ```
    *Populate this list now based on the user's project request. Mark all statuses as `false` initially.*

3.  **Create `progress.md`**: Create a file named `progress.md` to track a human-readable history of completed tasks. Initialize it with a "Pending" status.

4.  **Initialize Git**: Run `git init` (if not already done) and create an initial commit with these setup files.

### PHASE 2: THE DEVELOPMENT LOOP
Once initialization is complete, you will adopt the following strict loop for all future interactions. Do not deviate from this process:

1.  **READ STATE**: Look at `features.json`. Find the *first* feature where `"status": false`. This is your ONLY task for the current turn.
2.  **IMPLEMENT**: Write the code necessary to implement this single feature. Do not attempt to build multiple features at once.
3.  **TEST**:
    * If a test script exists, run it.
    * If frontend (e.g., Next.js), use a headless browser script (like Puppeteer) or write a temporary test script to verify the feature works as intended.
    * *Do not mark the feature complete until you have verified it works.*
4.  **UPDATE STATE**:
    * Update `features.json`: Set the current feature's `"status": true`.
    * Update `progress.md`: Append a log entry confirming the feature is done.
5.  **COMMIT**: Run `git add .` and `git commit -m "feat: [Feature Name] - Implemented and Verified"`.
6.  **STOP**: Inform the user the feature is done and ask for permission to proceed to the next one.

**CURRENT TASK:**
Please start **Phase 1** now. Analyze the project request (if provided) or ask me for the project idea so you can generate the `features.json` list.
````
</gemini_claude_code_instructions>

Replicate the process for us on the project that we are working on.
Make sure to create the file needed and update the claude.md

# Notes
Create a RAG Chatbot using Python and Django for backend and React JS for frontend
For the frameworks to be used, use LangChain, LangGraph, and Pydantic
This will be an agentic approach, wherein we will have multiple agents
For the vector database, we will be using Supabase
This will be deployed using Vercel + Railway
We will be using Gemini for our LLM

# Context
- Refer to @context\chatbot for my past Agentic RAG Chatbot in our system that uses LangChain/LangGraph/Pydantic.
- Refer to @context\django for the structure of a Django project and application. This is where you will reference the naming convention, coding standards and ethics

# Agents
1. RAG Chatbot Agent - Main conversational agent with retrieval-augmented generation
2. Agent Orchestrator - Coordinates and routes between different agents
3. Document Processing Agent - Handles PDFs, Word docs, spreadsheets
4. Conversation Agent - Handles simple users queries that is unrelated to any other Agents

# Tools
1. Web Search Tool - Searches the internet for current information
2. Vector Embedding Tool - Upserts and manages embeddings in Supabase
3. File Upload & Vectorization Tool - Processes user uploads into embeddings
4. DB Query Tool - Direct database queries to reduce token costs
5. Response Validator - Checks outputs for accuracy and hallucinations
6. Intent Classifier - Routes queries to appropriate agents

# Pages
1. Authentication Page
- Login Page
- Registration Page
2. Main Application Page
- Dashboard / Main Chatbot Page
- Sidebar
3. User & Settings Pages
- Profile Page
- Settings Page
4. Admin Page
- Admin Dashboard

In the UI/UX, make sure to add a toggle button. In this toggle button, it will be connected to the uploading of documents to the vector database. If it is toggled on, the user's uploaded document will be turn into vector embeddings and stored in our vector database. If it is turned off, the document will not be uploaded but rather will be the only focus of the chatbot for the user's queries.
Keep in mind that we are building this project to be a template for our future clients that wanted a chatbot, right now I am building a foundation that will be reused for future purposes.

