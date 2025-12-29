"""
RAG Chatbot Server
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path so imports work correctly
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from backend.src.rag.main import app

if __name__ == "__main__":
    import uvicorn

    # Check if we have the required environment variables
    if not os.getenv('NEON_DB_URL'):
        print("Warning: NEON_DB_URL environment variable not set")
        print("Please set it before running the server:")
        print("export NEON_DB_URL='your_postgres_connection_string'")

    if not os.getenv('ANTHROPIC_API_KEY'):
        print("Warning: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it before running the server:")
        print("export ANTHROPIC_API_KEY='your_anthropic_api_key'")

    # Run the server
    uvicorn.run(
        "backend.src.rag.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )