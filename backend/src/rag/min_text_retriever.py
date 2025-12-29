"""
Minimum Text Retrieval Module

This module implements logic to retrieve only the minimum required text
to answer each query, optimizing for context length while maintaining
relevance and accuracy.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
import re


class MinimumTextRetriever:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connection = None

    def connect_to_db(self):
        """Establish connection to Neon Serverless Postgres"""
        self.connection = psycopg2.connect(self.db_url)

    def _calculate_token_count(self, text: str) -> int:
        """Calculate approximate token count (simple word count for now)"""
        return len(text.split())

    def _find_relevant_sentences(self, text: str, query: str, max_sentences: int = 5) -> str:
        """
        Extract only the most relevant sentences from a text chunk based on the query
        """
        # Split text into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Score sentences based on query term matches
        query_terms = query.lower().split()
        scored_sentences = []

        for sentence in sentences:
            score = 0
            sentence_lower = sentence.lower()
            for term in query_terms:
                if term in sentence_lower:
                    score += 1
            scored_sentences.append((sentence, score))

        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in scored_sentences[:max_sentences] if s[1] > 0]

        return '. '.join(top_sentences) + '.'

    def retrieve_minimum_context(self, query: str, selected_text: Optional[str] = None,
                               max_tokens: int = 1500, min_tokens: int = 100) -> Dict[str, Any]:
        """
        Retrieve the minimum required text to answer a query, considering both
        search results and user-selected text, with prioritization.
        """
        if not self.connection:
            self.connect_to_db()

        result = {
            'context': '',
            'sources': [],
            'token_count': 0,
            'selected_text_used': bool(selected_text),
            'query': query,
            'is_sufficient': False  # Will be set based on context quality
        }

        # If user has selected specific text, use that as primary context
        if selected_text:
            result['context'] = selected_text
            result['token_count'] = self._calculate_token_count(selected_text)
            result['sources'].append('User Selected Text')
            result['is_sufficient'] = result['token_count'] >= min_tokens

            # If selected text is sufficient, return it
            if result['token_count'] <= max_tokens and result['is_sufficient']:
                return result

        # If we still need more context or the selected text wasn't sufficient,
        # search for relevant content in the database
        if result['token_count'] < max_tokens:
            remaining_tokens = max_tokens - result['token_count']

            # First, search for relevant chunks
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Use Postgres full-text search to find relevant content
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
                    LIMIT 10;
                """, (query, query))

                search_results = cursor.fetchall()

            # Process results to extract minimum relevant text
            for chunk in search_results:
                if remaining_tokens <= 0:
                    break

                # Extract only the most relevant sentences from this chunk
                relevant_excerpt = self._find_relevant_sentences(chunk['content'], query, max_sentences=3)

                if not relevant_excerpt.strip():
                    continue  # Skip if no relevant sentences found

                excerpt_token_count = self._calculate_token_count(relevant_excerpt)

                if excerpt_token_count <= remaining_tokens:
                    # Add this excerpt to our context
                    if result['context']:
                        result['context'] += "\n\n" + relevant_excerpt
                    else:
                        result['context'] = relevant_excerpt

                    result['token_count'] += excerpt_token_count
                    remaining_tokens -= excerpt_token_count

                    # Add source reference
                    source_ref = f"{chunk['chapter']}/{chunk['section']} - {chunk['title']}"
                    if source_ref not in result['sources']:
                        result['sources'].append(source_ref)

            # Determine if we have sufficient context
            result['is_sufficient'] = result['token_count'] >= min_tokens

        return result

    def retrieve_for_selected_text_only(self, selected_text: str, query: str) -> Dict[str, Any]:
        """
        Retrieve context when in SELECTED_TEXT_ONLY mode - only use the user-selected text
        """
        result = {
            'context': selected_text,
            'sources': ['User Selected Text'],
            'token_count': self._calculate_token_count(selected_text),
            'selected_text_used': True,
            'query': query,
            'is_sufficient': self._calculate_token_count(selected_text) >= 50  # Minimum for context
        }

        return result

    def retrieve_for_book_scope(self, query: str, max_tokens: int = 1500) -> Dict[str, Any]:
        """
        Retrieve context when in BOOK_SCOPE mode - search entire book content
        """
        if not self.connection:
            self.connect_to_db()

        result = {
            'context': '',
            'sources': [],
            'token_count': 0,
            'selected_text_used': False,
            'query': query,
            'is_sufficient': False
        }

        # Search for relevant content in the database
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Use Postgres full-text search to find relevant content
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
                LIMIT 15;
            """, (query, query))

            search_results = cursor.fetchall()

        # Process results to extract minimum relevant text
        remaining_tokens = max_tokens
        for chunk in search_results:
            if remaining_tokens <= 0:
                break

            # Extract only the most relevant sentences from this chunk
            relevant_excerpt = self._find_relevant_sentences(chunk['content'], query, max_sentences=2)

            if not relevant_excerpt.strip():
                continue  # Skip if no relevant sentences found

            excerpt_token_count = self._calculate_token_count(relevant_excerpt)

            if excerpt_token_count <= remaining_tokens:
                # Add this excerpt to our context
                if result['context']:
                    result['context'] += "\n\n" + relevant_excerpt
                else:
                    result['context'] = relevant_excerpt

                result['token_count'] += excerpt_token_count
                remaining_tokens -= excerpt_token_count

                # Add source reference
                source_ref = f"{chunk['chapter']}/{chunk['section']} - {chunk['title']}"
                if source_ref not in result['sources']:
                    result['sources'].append(source_ref)

        # Determine if we have sufficient context
        result['is_sufficient'] = result['token_count'] >= 100  # Minimum for context

        return result


def main():
    # Get database URL from environment variable
    db_url = os.getenv('NEON_DB_URL')
    if not db_url:
        raise ValueError("NEON_DB_URL environment variable is required")

    # Initialize the retriever
    retriever = MinimumTextRetriever(db_url)

    try:
        # Connect to database
        retriever.connect_to_db()

        print("Minimum text retrieval system initialized successfully!")

        # Example usage
        query = "ROS 2 installation process"
        result = retriever.retrieve_minimum_context(query, max_tokens=1000)

        print(f"\nContext retrieved for query: '{query}'")
        print(f"Token count: {result['token_count']}")
        print(f"Sources: {result['sources']}")
        print(f"Is sufficient: {result['is_sufficient']}")
        print(f"Context preview: {result['context'][:300]}...")

    except Exception as e:
        print(f"Error during minimum text retrieval: {str(e)}")
        raise
    finally:
        if retriever.connection:
            retriever.connection.close()


if __name__ == "__main__":
    main()