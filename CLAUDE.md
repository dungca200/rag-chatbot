# RAG Chatbot Template

## Project Overview
Production-ready RAG Chatbot template: Django + Next.js + LangChain/LangGraph + Supabase pgvector + Gemini LLM.

## Tech Stack
- **Backend**: Django 4.2+, DRF, LangChain, LangGraph, Pydantic
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind, Motion
- **Database**: PostgreSQL (Django), Supabase pgvector
- **LLM**: Gemini 1.5 Flash
- **Auth**: JWT (simplejwt)
- **Storage**: Supabase Storage
- **Deploy**: Railway (backend), Vercel (frontend)

## Architecture
- 4 Agents: Orchestrator, RAG, Conversation, Document Processor
- 6 Tools: Web Search, Vector Embedding, File Upload, DB Query, Response Validator, Intent Classifier
- SSE streaming, vectorization toggle (store/session mode)

---

## Guidelines

- In all interactions and commit messages, be extremely concise and sacrifice
  grammar for the sake of concision.

## PR Comments

<pr-comment-rule>
When I say to add a comment to a PR with a TODO on it, use
'checkbox' markdown format to add the TODO. For instance:

<example>
- [ ] A description of the todo goes here
</example>
</pr-comment-rule>

- When tagging Claude in GitHub issues, use '@claude'

## GitHub
- Your primary method for interacting with GitHub should be the GitHub CLI.

## Plans
- At the end of each plan, give me a list of unresolved questions to answer,
  if any. Make the questions extremely concise. Sacrifice grammar for the sake
  of concision.

## Development Workflow

### State Files
- `features.json` - Source of truth for feature status
- `progress.md` - Human-readable completion log

### Execution Loop
1. Read `features.json`, find first `status: false` with met dependencies
2. Implement ONLY that feature
3. Smoke test (server runs, endpoint 200, page renders)
4. If pass: update `features.json` status → true
5. Append to `progress.md`
6. Git commit: `feat(track): description`
7. Stop, ask to continue

### Context Recovery
New session? Read `features.json` + `git log --oneline -20` to resume.

### Commit Convention
```
feat(backend): description
feat(frontend-public): description
feat(frontend-portal): description
```

### Track Priority (for dependency ordering)
1. backend (APIs unblock frontend)
2. frontend-portal
3. frontend-public

