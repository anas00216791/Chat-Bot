"""
Database Initialization Script for RAG Chatbot

This script creates the necessary database tables for storing book content
with full-text search capabilities using Postgres tsvector and ts_rank.
"""
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def init_database(db_url):
    """
    Initialize the database with required tables and indexes for RAG system
    """
    # Connect to the database
    conn = psycopg2.connect(db_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    print("Creating book_chunks table with full-text search capabilities...")

    # Create the book_chunks table with tsvector column for full-text search
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_chunks (
            id SERIAL PRIMARY KEY,
            chunk_id VARCHAR(255) UNIQUE NOT NULL,
            chapter VARCHAR(255) NOT NULL,
            section VARCHAR(255),
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            token_count INTEGER DEFAULT 0,
            metadata JSONB DEFAULT '{}',
            tsvector_indexed TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create GIN index on the tsvector column for fast full-text search
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_book_chunks_tsvector_gin
        ON book_chunks USING GIN(tsvector_indexed);
    """)

    # Create additional indexes for efficient filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_book_chunks_chapter
        ON book_chunks(chapter);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_book_chunks_chunk_id
        ON book_chunks(chunk_id);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_book_chunks_title
        ON book_chunks(title);
    """)

    print("Database schema created successfully!")
    print("Tables and indexes:")
    print("- book_chunks: Main table for storing book content chunks")
    print("- idx_book_chunks_tsvector_gin: GIN index for full-text search")
    print("- idx_book_chunks_chapter: Index for chapter-based filtering")
    print("- idx_book_chunks_chunk_id: Index for chunk ID lookups")
    print("- idx_book_chunks_title: Index for title-based searches")

    # Verify the setup by checking if the table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'book_chunks'
        );
    """)

    table_exists = cursor.fetchone()[0]
    if table_exists:
        print("\n[OK] Database schema verification: SUCCESS")
    else:
        print("\n[ERROR] Database schema verification: FAILED")

    # Close connections
    cursor.close()
    conn.close()


def main():
    # Get database URL from environment variable
    db_url = os.getenv('NEON_DB_URL')
    if not db_url:
        raise ValueError("NEON_DB_URL environment variable is required")

    print("Initializing RAG Chatbot Database Schema...")
    print(f"Connecting to database...")

    try:
        init_database(db_url)
        print("\nDatabase initialization completed successfully!")
    except Exception as e:
        print(f"\nError during database initialization: {str(e)}")
        raise


if __name__ == "__main__":
    main()