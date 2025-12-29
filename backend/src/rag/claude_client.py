"""
Claude API Client Module

This module handles communication with the Claude API,
ensuring that only retrieved or selected text is sent to Claude,
with strict validation to prevent leakage of non-retrieved content.
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
from anthropic import AsyncAnthropic
import logging

from .retriever import BookContentRetriever
from .min_text_retriever import MinimumTextRetriever
from .prompt_templates import PromptBuilder, QueryMode
from .refusal_handler import RefusalHandler


class ClaudeRAGClient:
    """
    Claude API client that ensures only proper context is sent to Claude
    """

    def __init__(self, api_key: Optional[str] = None):
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.prompt_builder = PromptBuilder()
        self.refusal_handler = RefusalHandler()

    async def validate_context_before_send(self, context: str, original_query: str) -> Dict[str, Any]:
        """
        Validate that the context is appropriate before sending to Claude
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "filtered_context": context
        }

        # Check if context is empty
        if not context or len(context.strip()) == 0:
            validation_result["is_valid"] = False
            validation_result["issues"].append("Context is empty or contains only whitespace")
            return validation_result

        # Check context length (optional, based on Claude's limits)
        max_context_length = 100000  # Adjust based on Claude's context window
        if len(context) > max_context_length:
            validation_result["filtered_context"] = context[:max_context_length]
            validation_result["issues"].append(f"Context was too long ({len(context)} chars) and was truncated")

        # Verify context relevance to query (basic check)
        if original_query and context:
            query_words = set(original_query.lower().split())
            context_words = set(context.lower().split())
            common_words = query_words.intersection(context_words)

            if len(common_words) == 0 and len(query_words) > 0:
                validation_result["issues"].append("Context appears unrelated to query")

        return validation_result

    async def get_answer_from_claude(self, query: str, context: str, mode: QueryMode) -> Dict[str, Any]:
        """
        Get an answer from Claude using only the provided context
        """
        # Validate the context before sending to Claude
        validation = await self.validate_context_before_send(context, query)
        if not validation["is_valid"]:
            return {
                "success": False,
                "answer": self.refusal_handler.get_refusal_message(list(self.refusal_handler.refusal_messages.keys())[0]),
                "reason": "invalid_context",
                "validation_issues": validation["issues"]
            }

        # Build the appropriate prompt based on mode
        if mode == QueryMode.SELECTED_TEXT_ONLY:
            prompt_parts = self.prompt_builder.build_selected_text_prompt(
                validation["filtered_context"],
                query
            )
        else:
            prompt_parts = self.prompt_builder.build_book_scope_prompt(
                validation["filtered_context"],
                query
            )

        try:
            # Call Claude API with the prepared prompt
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Using Claude 3.5 Sonnet as specified
                max_tokens=1024,
                temperature=0.1,  # Low temperature for factual responses
                system=prompt_parts["system"],
                messages=[
                    {
                        "role": "user",
                        "content": prompt_parts["user"]
                    }
                ]
            )

            # Extract the answer from Claude's response
            answer = response.content[0].text if response.content else ""

            return {
                "success": True,
                "answer": answer,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }

        except Exception as e:
            logging.error(f"Error calling Claude API: {str(e)}")
            return {
                "success": False,
                "answer": self.refusal_handler.get_refusal_message(list(self.refusal_handler.refusal_messages.keys())[0]),
                "error": str(e)
            }

    async def get_answer_with_retrieval(self, query: str, mode: QueryMode,
                                      selected_text: Optional[str] = None,
                                      db_url: str = None) -> Dict[str, Any]:
        """
        Get an answer from Claude with automatic content retrieval
        """
        # Check if we're running in demo mode
        is_demo_mode = (
            (db_url == 'demo_postgres_connection_string' if db_url else os.getenv('NEON_DB_URL') == 'demo_postgres_connection_string') and
            self.api_key == 'demo_anthropic_api_key'
        )

        if is_demo_mode:
            # In demo mode, return a simulated response without database or API calls
            demo_answer = f"This is a demo response for your query: '{query}'. In production mode, the system would retrieve relevant content from the database and generate an answer using Claude AI."

            return {
                "success": True,
                "answer": demo_answer,
                "sources": ["Demo Mode"],
                "context_used": True,
                "usage": {
                    "input_tokens": len(demo_answer.split()),
                    "output_tokens": len(demo_answer.split())
                }
            }

        if not db_url:
            db_url = os.getenv('NEON_DB_URL')
            if not db_url:
                raise ValueError("NEON_DB_URL environment variable is required")

        # Initialize retrievers
        retriever = BookContentRetriever(db_url)
        min_text_retriever = MinimumTextRetriever(db_url)

        try:
            retriever.connect_to_db()
            min_text_retriever.connect_to_db()

            # Retrieve appropriate context based on mode
            if mode == QueryMode.SELECTED_TEXT_ONLY:
                if not selected_text:
                    return {
                        "success": False,
                        "answer": self.refusal_handler.get_refusal_message(
                            self.refusal_handler.refusal_messages.keys()[0]
                        ),
                        "reason": "selected_text_required"
                    }

                # Use only the selected text
                context_result = min_text_retriever.retrieve_for_selected_text_only(
                    selected_text,
                    query
                )
            else:
                # Retrieve from book content
                context_result = min_text_retriever.retrieve_for_book_scope(
                    query
                )

            # Check if context is sufficient
            if not context_result.get('is_sufficient', False):
                return {
                    "success": False,
                    "answer": self.refusal_handler.get_refusal_message(
                        self.refusal_handler.refusal_messages.keys()[0]
                    ),
                    "reason": "insufficient_context",
                    "sources": context_result.get('sources', [])
                }

            # Get answer from Claude using the retrieved context
            claude_response = await self.get_answer_from_claude(
                query,
                context_result['context'],
                mode
            )

            # Add sources to the response
            if claude_response['success']:
                claude_response['sources'] = context_result.get('sources', [])
                claude_response['context_used'] = True

            return claude_response

        finally:
            # Close database connections
            if retriever.connection:
                retriever.connection.close()
            if min_text_retriever.connection:
                min_text_retriever.connection.close()


def main():
    # Example usage would require API keys
    print("Claude RAG Client initialized")
    print("Note: This module requires valid ANTHROPIC_API_KEY and NEON_DB_URL environment variables")


if __name__ == "__main__":
    main()