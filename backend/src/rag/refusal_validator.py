"""
Refusal Behavior Validator Module

This module validates that the system correctly refuses to answer
when context is insufficient, maintaining zero hallucination.
"""
from typing import Dict, Any, List
from .refusal_handler import RefusalHandler, RefusalType
from .min_text_retriever import MinimumTextRetriever
from .constitution_enforcer import ConstitutionEnforcer
import os


class RefusalValidator:
    """
    Validates correct refusal behavior in the RAG system
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv('NEON_DB_URL')
        self.refusal_handler = RefusalHandler()
        self.constitution_enforcer = ConstitutionEnforcer()
        self.min_text_retriever = MinimumTextRetriever(self.db_url) if self.db_url else None

    def validate_no_context_refusal(self) -> Dict[str, Any]:
        """
        Validate refusal when no context is provided
        """
        print("Testing: No Context Refusal")

        result = self.refusal_handler.should_refuse_answer("", "What is ROS 2?")

        validation = {
            "test": "no_context_refusal",
            "should_refuse": result["should_refuse"],
            "refusal_type": result.get("refusal_type"),
            "correct_refusal": result["should_refuse"] and result["reason"] == "no_context",
            "message_contains_key_elements": "cannot answer" in result.get("message", "").lower() and
                                           "book content" in result.get("message", "").lower()
        }

        print(f"  Should refuse: {validation['should_refuse']}")
        print(f"  Correct refusal: {validation['correct_refusal']}")

        return validation

    def validate_insufficient_context_refusal(self) -> Dict[str, Any]:
        """
        Validate refusal when context is insufficient
        """
        print("\nTesting: Insufficient Context Refusal")

        # Test with very brief context
        brief_context = "ROS."
        question = "How do I install ROS 2?"

        result = self.refusal_handler.should_refuse_answer(brief_context, question, min_context_length=50)

        validation = {
            "test": "insufficient_context_refusal",
            "context_length": len(brief_context),
            "should_refuse": result["should_refuse"],
            "reason": result.get("reason"),
            "correct_refusal": result["should_refuse"] and result["reason"] == "context_too_brief",
            "message_contains_key_elements": "cannot answer" in result.get("message", "").lower() or
                                           "too brief" in result.get("message", "").lower()
        }

        print(f"  Context length: {validation['context_length']}")
        print(f"  Should refuse: {validation['should_refuse']}")
        print(f"  Correct refusal: {validation['correct_refusal']}")

        return validation

    def validate_no_relevance_refusal(self) -> Dict[str, Any]:
        """
        Validate refusal when context is not relevant to query
        """
        print("\nTesting: No Relevance Refusal")

        # Context about cats, question about ROS 2
        irrelevant_context = "Cats are feline animals that like to sleep and hunt mice."
        question = "How do I install ROS 2?"

        result = self.refusal_handler.should_refuse_answer(irrelevant_context, question)

        validation = {
            "test": "no_relevance_refusal",
            "should_refuse": result["should_refuse"],
            "reason": result.get("reason"),
            "correct_refusal": result["should_refuse"] and result["reason"] == "no_relevance",
            "message_contains_key_elements": "relevant" in result.get("message", "").lower() or
                                           "not appear" in result.get("message", "").lower()
        }

        print(f"  Should refuse: {validation['should_refuse']}")
        print(f"  Correct refusal: {validation['correct_refusal']}")

        return validation

    def validate_selected_text_insufficient_refusal(self) -> Dict[str, Any]:
        """
        Validate refusal in selected text only mode when text is insufficient
        """
        print("\nTesting: Selected Text Insufficient Refusal")

        # Test the selected text specific refusal
        refusal_result = self.refusal_handler.generate_selected_text_refusal(0)

        validation = {
            "test": "selected_text_insufficient_refusal",
            "refusal_type": refusal_result["refusal_type"],
            "message_contains_key_elements": "selected text" in refusal_result["message"].lower() and
                                           "cannot answer" in refusal_result["message"].lower(),
            "is_proper_refusal": refusal_result["should_refuse"]
        }

        print(f"  Is proper refusal: {validation['is_proper_refusal']}")
        print(f"  Message: {refusal_result['message'][:100]}...")

        return validation

    def validate_constitutional_refusal(self) -> Dict[str, Any]:
        """
        Validate refusal when constitutional principles would be violated
        """
        print("\nTesting: Constitutional Refusal")

        # Test constitution enforcement
        query = "What is the meaning of life?"
        context = "This book is about robotics and AI."  # Context not relevant to query
        response = "The meaning of life is 42."  # This would be hallucination

        compliance_check = self.constitution_enforcer.check_constitutional_compliance(query, context, response)

        validation = {
            "test": "constitutional_refusal",
            "is_compliant": compliance_check["is_compliant"],
            "has_issues": len(compliance_check["issues"]) > 0,
            "recommendations_made": len(compliance_check["recommendations"]) > 0,
            "should_refuse": not compliance_check["is_compliant"]
        }

        print(f"  Is compliant: {validation['is_compliant']}")
        print(f"  Has issues: {validation['has_issues']}")
        print(f"  Should refuse: {validation['should_refuse']}")

        return validation

    def validate_proper_refusal_messages(self) -> Dict[str, Any]:
        """
        Validate that refusal messages are standardized and appropriate
        """
        print("\nTesting: Proper Refusal Messages")

        # Check all refusal types have standardized messages
        all_refusals = self.refusal_handler.get_all_refusal_types()

        validation = {
            "test": "proper_refusal_messages",
            "total_refusal_types": len(all_refusals),
            "messages_validated": [],
            "all_messages_contain_key_elements": True
        }

        key_elements = ["cannot", "answer", "book", "content"]

        for refusal_type, message in all_refusals.items():
            message_lower = message.lower()
            contains_elements = all(element in message_lower for element in ["cannot", "answer"])
            is_book_related = any(word in message_lower for word in ["book", "content", "provided"])

            message_validation = {
                "type": refusal_type,
                "contains_basic_elements": contains_elements,
                "book_related": is_book_related,
                "length_appropriate": 50 <= len(message) <= 300
            }

            validation["messages_validated"].append(message_validation)

            if not (contains_elements and is_book_related):
                validation["all_messages_contain_key_elements"] = False

        print(f"  Total refusal types: {validation['total_refusal_types']}")
        print(f"  All messages contain key elements: {validation['all_messages_contain_key_elements']}")

        return validation

    def run_comprehensive_refusal_validation(self) -> Dict[str, Any]:
        """
        Run all refusal validation tests
        """
        print("Running comprehensive refusal validation...\n")

        validation_results = {
            "no_context": self.validate_no_context_refusal(),
            "insufficient_context": self.validate_insufficient_context_refusal(),
            "no_relevance": self.validate_no_relevance_refusal(),
            "selected_text_insufficient": self.validate_selected_text_insufficient_refusal(),
            "constitutional": self.validate_constitutional_refusal(),
            "proper_messages": self.validate_proper_refusal_messages()
        }

        # Calculate summary
        total_tests = len(validation_results)
        passed_tests = sum(1 for result in validation_results.values()
                          if result.get("correct_refusal", result.get("is_proper_refusal", result.get("should_refuse", False))))

        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "all_results": validation_results,
            "validation_passed": passed_tests == total_tests
        }

        print(f"\nRefusal Validation Summary:")
        print(f"  Tests passed: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"  Pass rate: {summary['pass_rate']:.1%}")
        print(f"  Overall validation passed: {summary['validation_passed']}")

        return summary

    def test_edge_cases(self) -> List[Dict[str, Any]]:
        """
        Test edge cases for refusal behavior
        """
        print("\nTesting edge cases for refusal behavior...")

        edge_cases = [
            {
                "name": "Empty strings",
                "context": "",
                "query": "",
                "expected_refusal": True
            },
            {
                "name": "Whitespace only context",
                "context": "   \n\n\t\t  ",
                "query": "What is ROS 2?",
                "expected_refusal": True
            },
            {
                "name": "Very long query, no context",
                "context": "",
                "query": "Can you provide a comprehensive detailed explanation of the complete installation process for ROS 2 including all dependencies, configuration steps, troubleshooting tips, and best practices?",
                "expected_refusal": True
            },
            {
                "name": "Single character context",
                "context": "A",
                "query": "What does this mean?",
                "expected_refusal": True
            }
        ]

        results = []
        for case in edge_cases:
            result = self.refusal_handler.should_refuse_answer(
                case["context"],
                case["query"]
            )

            case_result = {
                "case": case["name"],
                "expected_refusal": case["expected_refusal"],
                "actual_refusal": result["should_refuse"],
                "correct": case["expected_refusal"] == result["should_refuse"],
                "message": result.get("message", "")[:50] + "..." if result.get("message") else "No message"
            }

            results.append(case_result)
            print(f"  {case['name']}: Expected {case['expected_refusal']}, Got {case_result['actual_refusal']}, Correct: {case_result['correct']}")

        return results


def main():
    # Initialize the refusal validator
    validator = RefusalValidator()

    print("Refusal Behavior Validator")
    print("=" * 40)

    # Run comprehensive validation
    results = validator.run_comprehensive_refusal_validation()

    # Test edge cases
    print("\n" + "=" * 40)
    edge_results = validator.test_edge_cases()

    print(f"\nEdge case testing complete. {len([r for r in edge_results if r['correct']])}/{len(edge_results)} passed.")

    print(f"\nRefusal behavior validation complete!")
    print(f"Overall validation passed: {results['validation_passed']}")


if __name__ == "__main__":
    main()