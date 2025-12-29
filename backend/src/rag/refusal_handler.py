"""
Refusal Language Handler Module

This module standardizes refusal language across all prompts and scenarios,
ensuring consistent behavior when the system cannot answer questions.
"""
from typing import Dict, Any, Optional
from enum import Enum


class RefusalType(Enum):
    """Types of refusals that can occur"""
    INSUFFICIENT_CONTEXT = "insufficient_context"
    NO_RELEVANT_CONTENT = "no_relevant_content"
    SELECTED_TEXT_ONLY_INSUFFICIENT = "selected_text_only_insufficient"
    CONTEXT_TOO_BRIEF = "context_too_brief"
    NO_CONTEXT_PROVIDED = "no_context_provided"
    HALLUCINATION_PREVENTION = "hallucination_prevention"


class RefusalHandler:
    """
    Handles standardized refusal messages across all prompt scenarios
    """

    def __init__(self):
        self.refusal_messages = {
            RefusalType.INSUFFICIENT_CONTEXT: (
                "I cannot answer this question based on the provided book content. "
                "The retrieved information does not contain sufficient details to provide an accurate response. "
                "Please refer to the relevant sections of the book for the information you need."
            ),
            RefusalType.NO_RELEVANT_CONTENT: (
                "I cannot answer this question based on the provided book content. "
                "The retrieved information does not appear to contain relevant information for your query. "
                "Please check the book sections that might contain this information."
            ),
            RefusalType.SELECTED_TEXT_ONLY_INSUFFICIENT: (
                "I cannot answer this question based only on the selected text. "
                "The selected portion does not contain sufficient information to address your query. "
                "Please select a broader text segment or refer to other relevant sections of the book."
            ),
            RefusalType.CONTEXT_TOO_BRIEF: (
                "I cannot provide an accurate answer based on the provided context, as it is too brief to contain the necessary information. "
                "Please provide more context from the book or refer to the relevant sections directly."
            ),
            RefusalType.NO_CONTEXT_PROVIDED: (
                "I cannot answer this question without context from the book. "
                "No relevant book content was provided to answer your query. "
                "Please ensure you have selected text or that the book content is properly indexed."
            ),
            RefusalType.HALLUCINATION_PREVENTION: (
                "I cannot answer this question as it requires information not available in the provided book content. "
                "I am designed to answer only from the specific book content provided. "
                "Please consult the book directly for this information."
            )
        }

    def get_refusal_message(self, refusal_type: RefusalType, custom_context: Optional[str] = None) -> str:
        """
        Get the standardized refusal message for a specific refusal type
        """
        base_message = self.refusal_messages.get(refusal_type, self.refusal_messages[RefusalType.INSUFFICIENT_CONTEXT])

        if custom_context:
            # Add custom context to the base message if provided
            return f"{base_message} {custom_context}"

        return base_message

    def generate_context_insufficient_refusal(self, context_length: int = 0,
                                           min_required_length: int = 50) -> Dict[str, Any]:
        """
        Generate refusal for insufficient context scenarios
        """
        if context_length == 0:
            refusal_type = RefusalType.NO_CONTEXT_PROVIDED
        elif context_length < min_required_length:
            refusal_type = RefusalType.CONTEXT_TOO_BRIEF
        else:
            refusal_type = RefusalType.INSUFFICIENT_CONTEXT

        return {
            "refusal_type": refusal_type.value,
            "message": self.get_refusal_message(refusal_type),
            "should_refuse": True
        }

    def generate_selected_text_refusal(self, selected_text_length: int = 0) -> Dict[str, Any]:
        """
        Generate refusal for selected text only mode when insufficient
        """
        refusal_type = (RefusalType.SELECTED_TEXT_ONLY_INSUFFICIENT
                       if selected_text_length > 0
                       else RefusalType.NO_CONTEXT_PROVIDED)

        return {
            "refusal_type": refusal_type.value,
            "message": self.get_refusal_message(refusal_type),
            "should_refuse": True
        }

    def generate_no_relevant_content_refusal(self, query: str) -> Dict[str, Any]:
        """
        Generate refusal when no relevant content is found for the query
        """
        return {
            "refusal_type": RefusalType.NO_RELEVANT_CONTENT.value,
            "message": self.get_refusal_message(RefusalType.NO_RELEVANT_CONTENT),
            "query": query,
            "should_refuse": True
        }

    def should_refuse_answer(self, context: str, query: str, min_context_length: int = 50) -> Dict[str, Any]:
        """
        Determine if an answer should be refused based on context quality
        """
        result = {
            "should_refuse": False,
            "refusal_type": None,
            "message": None,
            "reason": None
        }

        # Check if context is empty
        if not context or len(context.strip()) == 0:
            refusal = self.generate_context_insufficient_refusal(0)
            result.update({
                "should_refuse": True,
                "refusal_type": refusal["refusal_type"],
                "message": refusal["message"],
                "reason": "no_context"
            })
            return result

        # Check if context is too brief
        context_length = len(context.strip())
        if context_length < min_context_length:
            refusal = self.generate_context_insufficient_refusal(context_length, min_context_length)
            result.update({
                "should_refuse": True,
                "refusal_type": refusal["refusal_type"],
                "message": refusal["message"],
                "reason": "context_too_brief"
            })
            return result

        # Check for relevance using simple keyword matching
        context_lower = context.lower()
        query_lower = query.lower()

        query_words = set(query_lower.split())
        context_words = set(context_lower.split())

        # If no meaningful overlap, consider it insufficient
        common_words = query_words.intersection(context_words)
        if len(common_words) == 0 and len(query_words) > 0:
            refusal = self.generate_no_relevant_content_refusal(query)
            result.update({
                "should_refuse": True,
                "refusal_type": refusal["refusal_type"],
                "message": refusal["message"],
                "reason": "no_relevance"
            })
            return result

        # Context seems adequate
        result["should_refuse"] = False
        return result

    def format_refusal_for_frontend(self, refusal_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format refusal result for frontend consumption
        """
        return {
            "success": False,
            "answer": refusal_result["message"],
            "sources": [],
            "context_used": False,
            "refusal_type": refusal_result["refusal_type"],
            "confidence": 0.0,
            "metadata": {
                "was_refused": True,
                "reason": refusal_result.get("reason", "insufficient_context")
            }
        }

    def get_all_refusal_types(self) -> Dict[str, str]:
        """
        Get all refusal types and their messages for reference
        """
        return {refusal_type.value: message for refusal_type, message in self.refusal_messages.items()}


def main():
    # Initialize the refusal handler
    handler = RefusalHandler()

    print("Refusal language handler system initialized successfully!")
    print(f"\nAvailable refusal types: {list(handler.get_all_refusal_types().keys())}")

    # Example usage
    print(f"\nExample refusal messages:")

    for refusal_type in RefusalType:
        message = handler.get_refusal_message(refusal_type)
        print(f"  {refusal_type.value}: {message[:80]}...")

    # Test context evaluation
    test_context = ""
    test_query = "How do I install ROS 2?"

    refusal_check = handler.should_refuse_answer(test_context, test_query)
    print(f"\nRefusal check for empty context: {refusal_check}")

    relevant_context = "ROS 2 installation involves several steps including setting up repositories and installing packages."
    refusal_check2 = handler.should_refuse_answer(relevant_context, test_query)
    print(f"Refusal check for relevant context: {refusal_check2}")


if __name__ == "__main__":
    main()