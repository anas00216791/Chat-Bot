"""
RAG Content Retrieval Module

This module implements text retrieval using Postgres-native search
(keyword and metadata-based search) to find relevant book content
for user queries.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging


class BookContentRetriever:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connection = None

    def connect_to_db(self):
        """Establish connection to Neon Serverless Postgres"""
        self.connection = psycopg2.connect(self.db_url)

    def search_content(self, query: str, limit: int = 5, chapter_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for content using Postgres full-text search
        Returns the most relevant chunks based on the query
        """
        if not self.connection:
            self.connect_to_db()

        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Use Postgres full-text search with ranking
            if chapter_filter:
                cursor.execute("""
                    SELECT
                        chunk_id,
                        chapter,
                        section,
                        title,
                        content,
                        token_count,
                        ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) AS rank
                    FROM book_chunks
                    WHERE
                        to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                        AND chapter = %s
                    ORDER BY rank DESC
                    LIMIT %s;
                """, (query, query, chapter_filter, limit))
            else:
                cursor.execute("""
                    SELECT
                        chunk_id,
                        chapter,
                        section,
                        title,
                        content,
                        token_count,
                        ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) AS rank
                    FROM book_chunks
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s;
                """, (query, query, limit))

            results = cursor.fetchall()

            # Convert RealDictRow objects to regular dictionaries
            return [dict(row) for row in results]

    def search_by_metadata(self, metadata_filters: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for content based on metadata filters
        Useful for finding content in specific chapters or sections
        """
        if not self.connection:
            self.connect_to_db()

        # Build the query dynamically based on provided metadata filters
        conditions = []
        params = []

        for key, value in metadata_filters.items():
            if key == 'chapter':
                conditions.append("chapter = %s")
                params.append(value)
            elif key == 'section':
                conditions.append("section = %s")
                params.append(value)
            elif key == 'title':
                conditions.append("title ILIKE %s")
                params.append(f"%{value}%")

        params.append(limit)

        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            if conditions:
                where_clause = " AND ".join(conditions)
                query = f"""
                    SELECT
                        chunk_id,
                        chapter,
                        section,
                        title,
                        content,
                        token_count
                    FROM book_chunks
                    WHERE {where_clause}
                    ORDER BY title
                    LIMIT %s;
                """
                cursor.execute(query, params)
            else:
                # If no conditions, return recent content
                cursor.execute("""
                    SELECT
                        chunk_id,
                        chapter,
                        section,
                        title,
                        content,
                        token_count
                    FROM book_chunks
                    ORDER BY updated_at DESC
                    LIMIT %s;
                """, (limit,))

            results = cursor.fetchall()
            return [dict(row) for row in results]

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific chunk by its ID"""
        if not self.connection:
            self.connect_to_db()

        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    chunk_id,
                    chapter,
                    section,
                    title,
                    content,
                    token_count,
                    metadata
                FROM book_chunks
                WHERE chunk_id = %s;
            """, (chunk_id,))

            result = cursor.fetchone()
            return dict(result) if result else None

    def get_chunks_by_chapter(self, chapter: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve all chunks from a specific chapter"""
        if not self.connection:
            self.connect_to_db()

        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    chunk_id,
                    chapter,
                    section,
                    title,
                    content,
                    token_count
                FROM book_chunks
                WHERE chapter = %s
                ORDER BY chunk_id
                LIMIT %s;
            """, (chapter, limit))

            results = cursor.fetchall()
            return [dict(row) for row in results]

    def get_relevant_context(self, query: str, selected_text: Optional[str] = None,
                           max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Get the most relevant context for a query, considering both search results
        and any user-selected text. Prioritizes selected text when present.
        """
        result = {
            'retrieved_content': [],
            'selected_text_used': bool(selected_text),
            'total_tokens': 0,
            'sources': []
        }

        # If user has selected specific text, prioritize that
        if selected_text:
            result['retrieved_content'].append({
                'type': 'selected_text',
                'content': selected_text,
                'title': 'User Selected Text',
                'chapter': 'selected',
                'section': 'selected',
                'token_count': len(selected_text.split())
            })
            result['total_tokens'] += len(selected_text.split())
            result['sources'].append('User Selected Text')

        # If we still have room and need more context, search the database
        if result['total_tokens'] < max_tokens:
            remaining_tokens = max_tokens - result['total_tokens']

            # Get search results based on the query
            search_results = self.search_content(query, limit=10)

            for chunk in search_results:
                chunk_token_count = chunk['token_count']

                if result['total_tokens'] + chunk_token_count <= max_tokens:
                    result['retrieved_content'].append({
                        'type': 'search_result',
                        'content': chunk['content'],
                        'title': chunk['title'],
                        'chapter': chunk['chapter'],
                        'section': chunk['section'],
                        'token_count': chunk_token_count
                    })
                    result['total_tokens'] += chunk_token_count
                    source_ref = f"{chunk['chapter']}/{chunk['section']}"
                    if source_ref not in result['sources']:
                        result['sources'].append(source_ref)

                if result['total_tokens'] >= max_tokens:
                    break

        return result


def main():
    # Get database URL from environment variable
    db_url = os.getenv('NEON_DB_URL')
    if not db_url:
        raise ValueError("NEON_DB_URL environment variable is required")

    # Initialize the retriever
    retriever = BookContentRetriever(db_url)

    try:
        # Connect to database
        retriever.connect_to_db()

        print("Book content retrieval system initialized successfully!")

        # Example usage
        query = "ROS 2 basics"
        results = retriever.search_content(query, limit=3)

        print(f"\nSearch results for '{query}':")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']} ({result['chapter']}/{result['section']})")
            print(f"   Preview: {result['content'][:100]}...")
            print()

    except Exception as e:
        print(f"Error during retrieval: {str(e)}")
        raise
    finally:
        if retriever.connection:
            retriever.connection.close()


if __name__ == "__main__":
    main()