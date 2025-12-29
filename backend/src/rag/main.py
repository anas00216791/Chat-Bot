"""
FastAPI Application for RAG Chatbot

This module implements FastAPI endpoints for the embedded RAG chatbot,
handling both book-scope and selected-text-only query modes.
"""
import os
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# Import our RAG modules
from .retriever import BookContentRetriever
from .min_text_retriever import MinimumTextRetriever
from .constitution_enforcer import ConstitutionEnforcer
from .prompt_templates import PromptBuilder, QueryMode
from .context_enforcer import ContextScopeEnforcer
from .refusal_handler import RefusalHandler
from .claude_client import ClaudeRAGClient
from .hallucination_prevention import HallucinationPrevention

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Book RAG Chatbot API",
    description="API for an embedded RAG chatbot that answers questions from book content",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    selected_text: Optional[str] = None
    mode: str = "book_scope"  # "book_scope" or "selected_text_only"
    max_tokens: int = 1500

class QueryResponse(BaseModel):
    success: bool
    answer: str
    sources: List[str]
    context_used: bool
    metadata: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    database_connected: bool

# Global instances (in production, use dependency injection)
retriever: BookContentRetriever = None
min_text_retriever: MinimumTextRetriever = None
constitution_enforcer: ConstitutionEnforcer = None
prompt_builder: PromptBuilder = None
context_enforcer: ContextScopeEnforcer = None
refusal_handler: RefusalHandler = None
claude_client: ClaudeRAGClient = None
hallucination_prevention: HallucinationPrevention = None


def init_rag_components():
    """Initialize all RAG components"""
    global retriever, min_text_retriever, constitution_enforcer, prompt_builder, context_enforcer, refusal_handler, claude_client, hallucination_prevention

    db_url = os.getenv('NEON_DB_URL')
    anthropic_api_key = os.getenv('965720276300-7fkkdp3igpc9voa5f413oiksb947n5ep.apps.googleusercontent.com')

    # Check if running in demo mode
    demo_mode = db_url == 'demo_postgres_connection_string' and anthropic_api_key == 'demo_anthropic_api_key'

    if not demo_mode:
        if not db_url:
            raise ValueError("NEON_DB_URL environment variable is required")

        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        retriever = BookContentRetriever(db_url)
        min_text_retriever = MinimumTextRetriever(db_url)
        # Connect to database
        retriever.connect_to_db()
        min_text_retriever.connect_to_db()
    else:
        # In demo mode, create dummy objects that won't connect to DB
        logger.info("Running in demo mode - initializing dummy retrievers")

        # Create a simple dummy object that mimics the retriever interface
        class DummyRetriever:
            def __init__(self):
                self.connection = None
            def connect_to_db(self):
                pass

        retriever = DummyRetriever()
        min_text_retriever = DummyRetriever()


    constitution_enforcer = ConstitutionEnforcer()
    prompt_builder = PromptBuilder()
    context_enforcer = ContextScopeEnforcer()
    refusal_handler = RefusalHandler()

    # Handle Claude client initialization for demo mode
    if demo_mode:
        # Use a demo API key for the Claude client in demo mode
        claude_api_key = anthropic_api_key
    else:
        claude_api_key = anthropic_api_key

    claude_client = ClaudeRAGClient(claude_api_key)
    hallucination_prevention = HallucinationPrevention()


@app.on_event("startup")
async def startup_event():
    """Initialize RAG components on startup"""
    logger.info("Initializing RAG components...")
    init_rag_components()
    logger.info("RAG components initialized successfully!")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check if running in demo mode
        demo_mode = os.getenv('NEON_DB_URL') == 'demo_postgres_connection_string'

        if demo_mode:
            return HealthResponse(
                status="healthy (demo mode)",
                database_connected=False  # In demo mode, database is not connected
            )
        else:
            # Test database connection by performing a simple query
            # Check if retriever has an active connection before trying to use it
            if hasattr(retriever, 'connection') and retriever.connection:
                with retriever.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return HealthResponse(
                    status="healthy",
                    database_connected=True
                )
            else:
                return HealthResponse(
                    status="unhealthy",
                    database_connected=False
                )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            database_connected=False
        )


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """
    Main query endpoint that handles both book-scope and selected-text-only modes
    """
    try:
        logger.info(f"Processing query: {request.query[:50]}... in mode: {request.mode}")

        # Validate mode
        if request.mode not in ["book_scope", "selected_text_only"]:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'book_scope' or 'selected_text_only'")

        # Check if running in demo mode
        demo_mode = os.getenv('NEON_DB_URL') == 'demo_postgres_connection_string'

        if demo_mode:
            # Return a demo response that simulates the system behavior
            demo_answer = f"This is a demo response for query: '{request.query}'. In production mode, the RAG system would retrieve relevant content from your robotics book and generate an answer using Claude AI. The system is running in demo mode and simulates responses without accessing the database."
            return QueryResponse(
                success=True,
                answer=demo_answer,
                sources=["Demo Mode"],
                context_used=True,
                metadata={
                    "was_refused": False,
                    "token_count": len(demo_answer.split()),
                    "selected_text_used": request.mode == "selected_text_only",
                    "demo_mode": True
                }
            )
        else:
            query_mode = QueryMode.SELECTED_TEXT_ONLY if request.mode == "selected_text_only" else QueryMode.BOOK_SCOPE

            # Get answer from Claude using only the proper context
            claude_response = await claude_client.get_answer_with_retrieval(
                query=request.query,
                mode=query_mode,
                selected_text=request.selected_text if query_mode == QueryMode.SELECTED_TEXT_ONLY else None,
                db_url=os.getenv('NEON_DB_URL')
            )

            if not claude_response['success']:
                # If Claude call failed, return appropriate refusal
                return QueryResponse(
                    success=False,
                    answer=claude_response.get('answer', 'Unable to process query'),
                    sources=claude_response.get('sources', []),
                    context_used=False,
                    metadata={
                        "was_refused": True,
                        "reason": claude_response.get('reason', 'processing_error'),
                        "error": claude_response.get('error', 'Unknown error')
                    }
                )

            # Apply constitution enforcement to the Claude response
            final_response = constitution_enforcer.enforce_constitution_rules(
                request.query,
                claude_response.get('context', ''),
                claude_response['answer']
            )

            # Validate the response meets constitutional requirements
            compliance_check = constitution_enforcer.check_constitutional_compliance(
                request.query,
                claude_response.get('context', ''),
                final_response
            )

            if not compliance_check['is_compliant']:
                # If there are compliance issues, return a refusal
                refusal_result = refusal_handler.get_refusal_message(
                    list(refusal_handler.refusal_messages.keys())[0]  # Use first refusal type
                )
                return QueryResponse(
                    success=False,
                    answer=refusal_result,
                    sources=claude_response.get('sources', []),
                    context_used=False,
                    metadata={
                        "was_refused": True,
                        "reason": "constitutional_violation",
                        "compliance_issues": compliance_check['issues']
                    }
                )

            return QueryResponse(
                success=True,
                answer=final_response,
                sources=claude_response.get('sources', []),
                context_used=claude_response.get('context_used', True),
                metadata={
                    "was_refused": False,
                    "token_count": claude_response.get('usage', {}).get('output_tokens', 0),
                    "input_tokens": claude_response.get('usage', {}).get('input_tokens', 0),
                    "selected_text_used": request.mode == "selected_text_only"
                }
            )

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/book-scope-query", response_model=QueryResponse)
async def book_scope_query_endpoint(request: QueryRequest) -> QueryResponse:
    """
    Dedicated endpoint for book-scope queries
    """
    # Force the mode to book_scope
    request.mode = "book_scope"
    return await query_endpoint(request)


@app.post("/selected-text-query", response_model=QueryResponse)
async def selected_text_query_endpoint(request: QueryRequest) -> QueryResponse:
    """
    Dedicated endpoint for selected-text-only queries
    """
    # Force the mode to selected_text_only
    request.mode = "selected_text_only"
    return await query_endpoint(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)