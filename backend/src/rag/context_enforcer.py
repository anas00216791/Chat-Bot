"""
Context Scope Enforcement Module

This module enforces context scope rules at the prompt level,
ensuring that only appropriate context is included in prompts.
"""
from typing import Dict, Any, List, Optional
from .prompt_templates import PromptBuilder, QueryMode


class ContextScopeEnforcer:
    """
    Enforces context scope rules to ensure proper context boundaries
    """

    def __init__(self):
        self.prompt_builder = PromptBuilder()

    def enforce_book_scope_rules(self, context: str, question: str) -> Dict[str, Any]:
        """
        Enforce rules for BOOK_SCOPE mode
        """
        enforcement_result = {
            "is_valid": True,
            "filtered_context": context,
            "prompt_parts": {},
            "violations": []
        }

        # Check if context is from book content (basic validation)
        if not context or len(context.strip()) == 0:
            enforcement_result["is_valid"] = False
            enforcement_result["violations"].append({
                "rule": "context_required",
                "message": "No context provided for book scope query"
            })
            return enforcement_result

        # Ensure context doesn't exceed reasonable limits
        max_context_length = 5000  # Adjust based on token limits
        if len(context) > max_context_length:
            # Truncate context to reasonable size while preserving meaning
            enforcement_result["filtered_context"] = context[:max_context_length]
            enforcement_result["violations"].append({
                "rule": "context_length",
                "message": f"Context truncated from {len(context)} to {max_context_length} characters"
            })

        # Build the appropriate prompt
        enforcement_result["prompt_parts"] = self.prompt_builder.build_book_scope_prompt(
            enforcement_result["filtered_context"],
            question
        )

        return enforcement_result

    def enforce_selected_text_only_rules(self, selected_text: str, question: str) -> Dict[str, Any]:
        """
        Enforce rules for SELECTED_TEXT_ONLY mode
        """
        enforcement_result = {
            "is_valid": True,
            "filtered_context": selected_text,
            "prompt_parts": {},
            "violations": []
        }

        # Check if selected text is provided
        if not selected_text or len(selected_text.strip()) == 0:
            enforcement_result["is_valid"] = False
            enforcement_result["violations"].append({
                "rule": "selected_text_required",
                "message": "No selected text provided for selected-text-only query"
            })
            return enforcement_result

        # Ensure selected text doesn't exceed reasonable limits
        max_text_length = 3000  # Adjust based on token limits
        if len(selected_text) > max_text_length:
            enforcement_result["filtered_context"] = selected_text[:max_text_length]
            enforcement_result["violations"].append({
                "rule": "selected_text_length",
                "message": f"Selected text truncated from {len(selected_text)} to {max_text_length} characters"
            })

        # Build the appropriate prompt
        enforcement_result["prompt_parts"] = self.prompt_builder.build_selected_text_prompt(
            enforcement_result["filtered_context"],
            question
        )

        return enforcement_result

    def validate_context_relevance(self, context: str, question: str) -> Dict[str, Any]:
        """
        Validate that the provided context is relevant to the question
        """
        validation_result = {
            "is_relevant": True,
            "confidence": 1.0,
            "issues": []
        }

        if not context or not question:
            validation_result["is_relevant"] = False
            validation_result["confidence"] = 0.0
            return validation_result

        # Simple keyword overlap check
        context_lower = context.lower()
        question_lower = question.lower()

        question_words = set(question_lower.split())
        context_words = set(context_lower.split())

        # Calculate overlap
        common_words = question_words.intersection(context_words)
        if len(common_words) == 0:
            validation_result["is_relevant"] = False
            validation_result["confidence"] = 0.1
            validation_result["issues"].append("No keyword overlap between question and context")
        else:
            overlap_ratio = len(common_words) / len(question_words)
            validation_result["confidence"] = min(overlap_ratio, 1.0)

            if overlap_ratio < 0.2:  # Less than 20% overlap
                validation_result["is_relevant"] = False
                validation_result["issues"].append(f"Low keyword overlap: {overlap_ratio:.2%}")

        return validation_result

    def enforce_context_boundary(self, mode: QueryMode, context: str, selected_text: Optional[str],
                               question: str) -> Dict[str, Any]:
        """
        Main method to enforce context boundaries based on mode
        """
        if mode == QueryMode.BOOK_SCOPE:
            result = self.enforce_book_scope_rules(context, question)
        elif mode == QueryMode.SELECTED_TEXT_ONLY:
            result = self.enforce_selected_text_only_rules(selected_text or "", question)
        else:
            raise ValueError(f"Unknown query mode: {mode}")

        # Additional validation for relevance
        if result["is_valid"]:
            validation = self.validate_context_relevance(
                result["filtered_context"],
                question
            )
            result["relevance_validation"] = validation

            if not validation["is_relevant"]:
                result["is_valid"] = False
                result["violations"].extend(validation["issues"])

        return result

    def get_context_usage_report(self, original_context: str, filtered_context: str) -> Dict[str, Any]:
        """
        Generate a report on how context was used and filtered
        """
        return {
            "original_length": len(original_context) if original_context else 0,
            "filtered_length": len(filtered_context) if filtered_context else 0,
            "reduction_percentage": (
                (len(original_context) - len(filtered_context)) / len(original_context) * 100
                if original_context and len(original_context) > 0 else 0
            ),
            "was_filtered": (original_context and len(original_context) != len(filtered_context))
        }


def main():
    # Initialize the context scope enforcer
    enforcer = ContextScopeEnforcer()

    print("Context scope enforcement system initialized successfully!")

    # Example usage
    question = "How do I install ROS 2?"
    context = "ROS 2 installation requires following the official documentation. Visit the ROS 2 website for detailed instructions..."

    # Test book scope enforcement
    book_scope_result = enforcer.enforce_context_boundary(
        QueryMode.BOOK_SCOPE,
        context,
        None,
        question
    )

    print(f"\nBook scope enforcement result:")
    print(f"Is valid: {book_scope_result['is_valid']}")
    print(f"Violations: {book_scope_result['violations']}")
    print(f"Filtered context length: {len(book_scope_result['filtered_context'])}")

    # Test selected text enforcement
    selected_text = "ROS 2 can be installed following these steps..."
    selected_text_result = enforcer.enforce_context_boundary(
        QueryMode.SELECTED_TEXT_ONLY,
        None,
        selected_text,
        question
    )

    print(f"\nSelected text enforcement result:")
    print(f"Is valid: {selected_text_result['is_valid']}")
    print(f"Violations: {selected_text_result['violations']}")
    print(f"Filtered context length: {len(selected_text_result['filtered_context'])}")


if __name__ == "__main__":
    main()