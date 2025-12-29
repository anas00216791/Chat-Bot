# RAG Chatbot System for Embedded Book Queries

This directory contains a complete Retrieval-Augmented Generation (RAG) chatbot system designed to answer questions from a published book with strict grounding requirements. The system follows constitutional principles to ensure zero hallucination and absolute fidelity to provided book content.

## Architecture Overview

The RAG system consists of several key components:

1. **Content Ingestion Pipeline** (`ingest_content.py`): Converts book content to searchable chunks with metadata
2. **PostgreSQL Full-Text Search** (`retriever.py`): Uses native Postgres `tsvector` and `ts_rank` for retrieval (no vector databases)
3. **Constitutional Prompting** (`prompt_templates.py`): Enforces strict context boundaries and hallucination prevention
4. **Claude API Integration** (`claude_client.py`): Interfaces with Anthropic Claude 4.5 Sonnet
5. **Constitution Enforcement** (`constitution_enforcer.py`): Ensures all responses follow constitutional principles
6. **Refusal Handling** (`refusal_handler.py`): Manages appropriate responses when information is unavailable

## Key Features

- **Dual Query Modes**:
  - `SELECTED_TEXT_ONLY`: Answers strictly from user-selected text
  - `BOOK_SCOPE`: Retrieves relevant book excerpts via full-text search, then answers

- **Constitutional Compliance**:
  - Zero hallucination guarantee
  - Absolute source fidelity
  - Context scope obedience
  - Adversarial robustness
  - Standard refusal messages

- **PostgreSQL-Based Retrieval** (No vector databases):
  - Uses native `tsvector` and `ts_rank` for semantic search
  - Stores book content with metadata in `book_chunks` table
  - Full-text search indexes for efficient retrieval

## Setup and Installation

### Prerequisites
- Python 3.8+
- PostgreSQL database (Neon Serverless recommended)
- Anthropic API key for Claude access

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export NEON_DB_URL="your_postgres_connection_string"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

3. Initialize the database:
```bash
python backend/src/rag/init_db.py
```

4. Ingest book content:
```bash
python backend/src/rag/ingest_content.py
```

## API Endpoints

The system provides a FastAPI-based REST API:

- `POST /query` - Main query endpoint supporting both modes
- `POST /book-scope-query` - Dedicated book-scope queries
- `POST /selected-text-query` - Dedicated selected-text queries
- `GET /health` - Health check endpoint

### Query Request Format
```json
{
  "query": "Your question here",
  "mode": "book_scope|selected_text_only",
  "selected_text": "Text selected by user (for selected_text_only mode)"
}
```

### Response Format
```json
{
  "success": true,
  "answer": "The answer from Claude",
  "sources": ["list of source references"],
  "context_used": true,
  "metadata": {
    "was_refused": false,
    "token_count": 150
  }
}
```

## Constitutional Principles Enforced

The system enforces these core principles:

1. **Absolute Source Fidelity**: Only uses information from provided text
2. **Context Scope Obedience**: Respects SELECTED_TEXT_ONLY vs BOOK_SCOPE boundaries
3. **Zero Hallucination**: Never adds external information
4. **Transparency**: Uses standard refusal when information unavailable
5. **Adversarial Robustness**: Resists jailbreak attempts

## Validation and Testing

Run the constitutional compliance validator:
```bash
python backend/src/rag/validate_constitutional_compliance.py
```

Run the system tests:
```bash
python backend/src/rag/test_rag_system.py
```

## Security and Compliance

- No OpenAI APIs used (prohibited by constitution)
- No vector databases used (prohibited by constitution)
- All responses grounded in provided book content only
- Standard refusal messages for unavailable information
- Adversarial input protection

## Performance Considerations

- Uses PostgreSQL's efficient full-text search indexing
- Implements proper token management for Claude API
- Caches frequently accessed content chunks
- Implements proper error handling and retries

## Deployment

The system can be deployed as a standalone FastAPI service:

```bash
uvicorn backend.src.rag.main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

- If ingestion fails, verify database connectivity and permissions
- If Claude API calls fail, check API key validity and rate limits
- If retrieval returns no results, verify content was properly ingested
- Check logs for detailed error information