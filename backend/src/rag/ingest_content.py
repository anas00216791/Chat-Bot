"""
RAG Content Ingestion Script

This script ingests Docusaurus book content from markdown files,
converts it to structured text chunks with stable identifiers,
and stores it in Neon Serverless Postgres with metadata.
"""
import os
import re
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import markdown
from bs4 import BeautifulSoup
import yaml


class BookContentIngestor:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connection = None

    def connect_to_db(self):
        """Establish connection to Neon Serverless Postgres"""
        self.connection = psycopg2.connect(self.db_url)

    def create_tables(self):
        """Create necessary tables for storing book content with full-text search"""
        with self.connection.cursor() as cursor:
            # Create table for book chunks with tsvector for full-text search
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

        self.connection.commit()

    def extract_content_from_markdown(self, file_path: str) -> Dict[str, Any]:
        """Extract content from a Docusaurus markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter if present
        frontmatter = {}
        content_body = content

        # Look for YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    content_body = parts[2]
                except yaml.YAMLError:
                    # If YAML parsing fails, treat entire content as body
                    pass

        # Convert markdown to plain text
        html = markdown.markdown(content_body)
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text()

        # Extract title from frontmatter or first heading
        title = frontmatter.get('title', '')
        if not title:
            # Look for first heading in content
            lines = content_body.split('\n')
            for line in lines:
                if line.strip().startswith('# '):
                    title = line.strip()[2:]  # Remove '# ' prefix
                    break

        # If still no title, use filename
        if not title:
            title = Path(file_path).stem.replace('-', ' ').title()

        return {
            'title': title,
            'content': plain_text.strip(),
            'frontmatter': frontmatter,
            'file_path': file_path
        }

    def chunk_text(self, text: str, max_chunk_size: int = 1000) -> List[Dict[str, str]]:
        """Split text into semantically meaningful chunks"""
        chunks = []

        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        current_chunk = ""
        current_size = 0

        for paragraph in paragraphs:
            # If adding this paragraph would exceed the chunk size
            if current_size + len(paragraph) > max_chunk_size and current_chunk:
                # Save the current chunk
                chunks.append({
                    'content': current_chunk.strip(),
                    'token_count': len(current_chunk.split())
                })

                # Start a new chunk with the current paragraph
                current_chunk = paragraph
                current_size = len(paragraph)
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_size += len(paragraph)

        # Add the final chunk if it has content
        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'token_count': len(current_chunk.split())
            })

        return chunks

    def generate_chunk_id(self, chapter: str, section: str, chunk_index: int, content: str) -> str:
        """Generate a stable, unique identifier for a chunk"""
        # Create a hash of the content to ensure uniqueness
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

        # Combine with location information
        chunk_id = f"{chapter}_{section}_{chunk_index:03d}_{content_hash}"
        return chunk_id

    def ingest_book_content(self, book_path: str):
        """Ingest all book content from the specified path"""
        book_dir = Path(book_path)

        # Get all markdown files in the book directory
        md_files = list(book_dir.rglob("*.md"))

        print(f"Found {len(md_files)} markdown files to process")

        for md_file in md_files:
            print(f"Processing: {md_file}")

            # Extract content from markdown
            extracted = self.extract_content_from_markdown(str(md_file))

            # Determine chapter and section from file path
            relative_path = md_file.relative_to(book_dir)
            path_parts = str(relative_path).split(os.sep)

            chapter = path_parts[0] if len(path_parts) > 1 else 'intro'
            section = path_parts[1] if len(path_parts) > 2 else 'index'

            # If the file is an index.md, use the parent directory as the section
            if path_parts[-1] in ['index.md', 'intro.md']:
                section = path_parts[-1].replace('.md', '')
            else:
                section = path_parts[-1].replace('.md', '')

            # Chunk the content
            chunks = self.chunk_text(extracted['content'])

            print(f"  - Generated {len(chunks)} chunks")

            # Insert each chunk into the database
            with self.connection.cursor() as cursor:
                for i, chunk in enumerate(chunks):
                    chunk_id = self.generate_chunk_id(chapter, section, i, chunk['content'])

                    # Create content hash for change detection
                    content_hash = hashlib.sha256(chunk['content'].encode('utf-8')).hexdigest()

                    # Insert or update the chunk
                    cursor.execute("""
                        INSERT INTO book_chunks
                        (chunk_id, chapter, section, title, content, content_hash, token_count, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (chunk_id)
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            content_hash = EXCLUDED.content_hash,
                            token_count = EXCLUDED.token_count,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        """, (
                            chunk_id,
                            chapter,
                            section,
                            extracted['title'],
                            chunk['content'],
                            content_hash,
                            chunk['token_count'],
                            json.dumps({
                                'source_file': str(md_file),
                                'original_title': extracted['title'],
                                'frontmatter': extracted['frontmatter']
                            })
                        ))

        self.connection.commit()
        print(f"Successfully ingested book content into database")


def main():
    # Get database URL from environment variable
    db_url = os.getenv('NEON_DB_URL')
    if not db_url:
        raise ValueError("NEON_DB_URL environment variable is required")

    # Get book path from command line or default to my-book/docs
    book_path = os.getenv('BOOK_PATH', 'my-book/docs')

    # Initialize the ingestor
    ingestor = BookContentIngestor(db_url)

    try:
        # Connect to database
        ingestor.connect_to_db()

        # Create tables if they don't exist
        ingestor.create_tables()

        # Ingest the book content
        ingestor.ingest_book_content(book_path)

        print("Book content ingestion completed successfully!")

    except Exception as e:
        print(f"Error during ingestion: {str(e)}")
        raise
    finally:
        if ingestor.connection:
            ingestor.connection.close()


if __name__ == "__main__":
    main()