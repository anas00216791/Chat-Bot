"""
Claude Prompt Templates Module

This module defines system and user prompt templates for the RAG chatbot,
enforcing context scope rules and standardizing refusal language.
"""
from typing import Dict, Any, List, Optional
from enum import Enum


class QueryMode(Enum):
    BOOK_SCOPE = "book_scope"
    SELECTED_TEXT_ONLY = "selected_text_only"


class PromptTemplates:
    """
    Class containing all prompt templates for the RAG system
    """

    def __init__(self):
        self.system_prompt = self._create_system_prompt()
        self.user_prompt_templates = self._create_user_prompt_templates()

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt that enforces all constraints
        """
        return """You are an AI assistant embedded in a published book to answer reader questions.
You must strictly follow these rules:

1. ONLY use information provided in the CONTEXT to answer questions
2. NEVER hallucinate or make up information not present in the CONTEXT
3. NEVER use external knowledge or general world knowledge
4. If the CONTEXT does not contain sufficient information to answer a query, explicitly refuse to answer
5. Always cite specific book sections when providing information
6. Maintain academic integrity and accuracy as specified in the project constitution

Your responses should be clear, concise, and directly based on the provided context.
Do not add information from your general knowledge or external sources.
If you cannot answer based on the provided context, clearly state this limitation."""

    def _create_user_prompt_templates(self) -> Dict[str, str]:
        """
        Create user prompt templates for different query modes
        """
        return {
            QueryMode.BOOK_SCOPE.value: """Given the following context from the book, please answer the user's question.

CONTEXT:
{context}

QUESTION: {question}

Please provide an accurate answer based only on the information in the CONTEXT. If the context does not contain sufficient information to answer the question, please state that you cannot answer based on the provided book content and suggest the user check the relevant book sections.

Answer:""",

            QueryMode.SELECTED_TEXT_ONLY.value: """Based ONLY on the following selected text, please answer the user's question.

SELECTED TEXT:
{selected_text}

QUESTION: {question}

Please provide an answer based ONLY on the information in the SELECTED TEXT. Do not use any other knowledge. If the selected text does not contain sufficient information to answer the question, please state that you cannot answer based only on the selected text.

Answer:"""
        }

    def get_system_prompt(self) -> str:
        """Get the system prompt"""
        return self.system_prompt

    def get_user_prompt(self, mode: QueryMode, context: str, question: str, selected_text: Optional[str] = None) -> str:
        """
        Get a formatted user prompt based on the query mode
        """
        if mode == QueryMode.SELECTED_TEXT_ONLY and selected_text:
            return self.user_prompt_templates[QueryMode.SELECTED_TEXT_ONLY.value].format(
                selected_text=selected_text,
                question=question
            )
        else:
            # For BOOK_SCOPE mode or when no selected text is provided
            return self.user_prompt_templates[QueryMode.BOOK_SCOPE.value].format(
                context=context,
                question=question
            )

    def get_refusal_template(self) -> str:
        """
        Get the standardized refusal template
        """
        return """I cannot answer this question based on the provided context. The book content does not contain sufficient information to address your query. Please refer to the relevant sections of the book for accurate information."""

    def get_context_insufficient_template(self) -> str:
        """
        Get template for when context is insufficient
        """
        return """I cannot answer this question based on the provided context. The retrieved information does not contain the necessary details to provide an accurate response. Please check the relevant book sections for the information you need."""

    def get_selected_text_insufficient_template(self) -> str:
        """
        Get template for when selected text is insufficient
        """
        return """I cannot answer this question based only on the selected text. The selected portion does not contain sufficient information to address your query. Please select a broader text segment or refer to other relevant sections of the book."""


class PromptBuilder:
    """
    Helper class to build prompts with proper formatting and validation
    """

    def __init__(self):
        self.templates = PromptTemplates()

    def build_book_scope_prompt(self, context: str, question: str) -> Dict[str, str]:
        """
        Build a complete prompt for book scope queries
        """
        system_prompt = self.templates.get_system_prompt()
        user_prompt = self.templates.get_user_prompt(
            mode=QueryMode.BOOK_SCOPE,
            context=context,
            question=question
        )

        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def build_selected_text_prompt(self, selected_text: str, question: str) -> Dict[str, str]:
        """
        Build a complete prompt for selected text only queries
        """
        system_prompt = self.templates.get_system_prompt()
        user_prompt = self.templates.get_user_prompt(
            mode=QueryMode.SELECTED_TEXT_ONLY,
            context="",  # Not used for selected text mode
            question=question,
            selected_text=selected_text
        )

        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def build_refusal_response(self) -> str:
        """
        Build a standardized refusal response
        """
        return self.templates.get_refusal_template()

    def build_context_insufficient_response(self) -> str:
        """
        Build a response for insufficient context
        """
        return self.templates.get_context_insufficient_template()

    def build_selected_text_insufficient_response(self) -> str:
        """
        Build a response for insufficient selected text
        """
        return self.templates.get_selected_text_insufficient_template()


def main():
    # Initialize the prompt builder
    prompt_builder = PromptBuilder()

    print("Prompt templates system initialized successfully!")
    print(f"\nSystem prompt length: {len(prompt_builder.templates.get_system_prompt())} characters")

    # Example usage
    context = "ROS 2 is a flexible framework for developing robot applications. It provides a collection of libraries and tools that help developers create robot applications."
    question = "What is ROS 2?"

    book_scope_prompt = prompt_builder.build_book_scope_prompt(context, question)
    print(f"\nExample Book Scope Prompt:")
    print(f"System preview: {book_scope_prompt['system'][:100]}...")
    print(f"User preview: {book_scope_prompt['user'][:100]}...")

    selected_text = "ROS 2 is designed for large development efforts."
    selected_text_prompt = prompt_builder.build_selected_text_prompt(selected_text, question)
    print(f"\nExample Selected Text Prompt:")
    print(f"System preview: {selected_text_prompt['system'][:100]}...")
    print(f"User preview: {selected_text_prompt['user'][:100]}...")

    print(f"\nRefusal template: {prompt_builder.build_refusal_response()}")


if __name__ == "__main__":
    main()