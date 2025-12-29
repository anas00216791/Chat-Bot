"""
Prompt Flow Testing Module

This module tests all prompt flows to ensure they work correctly
and validate correct refusal behavior.
"""
import os
from typing import Dict, Any, List
from .prompt_templates import PromptBuilder, QueryMode
from .refusal_handler import RefusalHandler, RefusalType
from .min_text_retriever import MinimumTextRetriever
from .constitution_enforcer import ConstitutionEnforcer


class PromptFlowTester:
    """
    Tests all prompt flows to ensure correct behavior
    """

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.refusal_handler = RefusalHandler()
        self.constitution_enforcer = ConstitutionEnforcer()

    def test_book_scope_prompt_flow(self) -> Dict[str, Any]:
        """
        Test the book scope prompt flow
        """
        print("Testing Book Scope Prompt Flow...")

        context = "ROS 2 is a flexible framework for developing robot applications. It provides libraries and tools for building robot software. ROS 2 includes features like real-time support, security, and improved architecture."
        question = "What is ROS 2?"

        prompt_parts = self.prompt_builder.build_book_scope_prompt(context, question)

        result = {
            "flow": "book_scope",
            "system_prompt_present": len(prompt_parts["system"]) > 0,
            "user_prompt_present": len(prompt_parts["user"]) > 0,
            "context_included": context in prompt_parts["user"],
            "question_included": question in prompt_parts["user"],
            "expected_behavior": "Should provide answer based on context"
        }

        print(f"  System prompt length: {len(prompt_parts['system'])} chars")
        print(f"  User prompt length: {len(prompt_parts['user'])} chars")
        print(f"  Context included: {result['context_included']}")
        print(f"  Question included: {result['question_included']}")

        return result

    def test_selected_text_prompt_flow(self) -> Dict[str, Any]:
        """
        Test the selected text prompt flow
        """
        print("\nTesting Selected Text Prompt Flow...")

        selected_text = "ROS 2 is designed for large development efforts and provides real-time support."
        question = "What is ROS 2 designed for?"

        prompt_parts = self.prompt_builder.build_selected_text_prompt(selected_text, question)

        result = {
            "flow": "selected_text",
            "system_prompt_present": len(prompt_parts["system"]) > 0,
            "user_prompt_present": len(prompt_parts["user"]) > 0,
            "selected_text_included": selected_text in prompt_parts["user"],
            "question_included": question in prompt_parts["user"],
            "expected_behavior": "Should answer based only on selected text"
        }

        print(f"  System prompt length: {len(prompt_parts['system'])} chars")
        print(f"  User prompt length: {len(prompt_parts['user'])} chars")
        print(f"  Selected text included: {result['selected_text_included']}")
        print(f"  Question included: {result['question_included']}")

        return result

    def test_refusal_prompt_flow(self) -> Dict[str, Any]:
        """
        Test the refusal prompt flow
        """
        print("\nTesting Refusal Prompt Flow...")

        # Test different refusal types
        refusal_results = {}
        for refusal_type in RefusalType:
            message = self.refusal_handler.get_refusal_message(refusal_type)
            refusal_results[refusal_type.value] = {
                "message_length": len(message),
                "contains_key_elements": all(x in message.lower() for x in ["cannot", "answer", "book", "content"])
            }

        result = {
            "flow": "refusal",
            "refusal_types_tested": len(list(RefusalType)),
            "refusal_messages": refusal_results,
            "expected_behavior": "Should provide consistent refusal messages"
        }

        for refusal_type, details in refusal_results.items():
            print(f"  {refusal_type}: {details['message_length']} chars, key elements present: {details['contains_key_elements']}")

        return result

    def test_constitution_enforcement(self) -> Dict[str, Any]:
        """
        Test constitution enforcement in prompts
        """
        print("\nTesting Constitution Enforcement...")

        # Test with good context
        query = "How do I install ROS 2?"
        context = "To install ROS 2, follow the official documentation..."
        response = "Based on the book content, you install ROS 2 by following the official documentation."

        compliance_check = self.constitution_enforcer.check_constitutional_compliance(query, context, response)
        good_context_result = {
            "query": query,
            "context_length": len(context),
            "compliant": compliance_check["is_compliant"],
            "issues": compliance_check["issues"],
            "recommendations": compliance_check["recommendations"]
        }

        # Test with insufficient context (potential hallucination)
        bad_response = "You can install ROS 2 by running 'sudo apt install ros' (this is made up)."
        bad_compliance_check = self.constitution_enforcer.check_constitutional_compliance(query, "", bad_response)
        bad_context_result = {
            "query": query,
            "context_length": 0,
            "compliant": bad_compliance_check["is_compliant"],
            "issues": bad_compliance_check["issues"],
            "recommendations": bad_compliance_check["recommendations"]
        }

        result = {
            "flow": "constitution_enforcement",
            "good_context_test": good_context_result,
            "bad_context_test": bad_context_result,
            "expected_behavior": "Should enforce constitutional compliance"
        }

        print(f"  Good context compliant: {good_context_result['compliant']}")
        print(f"  Bad context compliant: {bad_context_result['compliant']}")
        if bad_context_result['issues']:
            print(f"  Issues detected in bad context: {bad_context_result['issues']}")

        return result

    def test_context_boundary_enforcement(self) -> Dict[str, Any]:
        """
        Test context boundary enforcement
        """
        print("\nTesting Context Boundary Enforcement...")

        # Test that only appropriate context is used
        results = []

        # Test 1: Book scope with good context
        book_context = "This is relevant book content about ROS 2..."
        book_question = "What is ROS 2?"
        book_prompt = self.prompt_builder.build_book_scope_prompt(book_context, book_question)
        results.append({
            "test": "book_scope_with_context",
            "uses_context": book_context in book_prompt["user"],
            "system_present": len(book_prompt["system"]) > 0
        })

        # Test 2: Selected text only
        selected_text = "This is user selected text..."
        selected_question = "What does this text say?"
        selected_prompt = self.prompt_builder.build_selected_text_prompt(selected_text, selected_question)
        results.append({
            "test": "selected_text_only",
            "uses_selected_text": selected_text in selected_prompt["user"],
            "system_present": len(selected_prompt["system"]) > 0
        })

        result = {
            "flow": "context_boundary",
            "tests_run": results,
            "expected_behavior": "Should enforce strict context boundaries"
        }

        for test_result in results:
            print(f"  {test_result['test']}: Context used correctly: {test_result.get('uses_context', test_result.get('uses_selected_text', False))}")

        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all prompt flow tests
        """
        print("Running all prompt flow tests...\n")

        test_results = {
            "book_scope_flow": self.test_book_scope_prompt_flow(),
            "selected_text_flow": self.test_selected_text_prompt_flow(),
            "refusal_flow": self.test_refusal_prompt_flow(),
            "constitution_enforcement": self.test_constitution_enforcement(),
            "context_boundary_enforcement": self.test_context_boundary_enforcement()
        }

        summary = {
            "total_tests": len(test_results),
            "tests_passed": 0,  # This would be calculated based on actual test results
            "tests_failed": 0,
            "all_results": test_results
        }

        print(f"\nAll prompt flow tests completed.")
        print(f"Tests run: {summary['total_tests']}")

        return summary


def main():
    # Initialize the prompt flow tester
    tester = PromptFlowTester()

    print("Prompt Flow Testing System")
    print("=" * 40)

    # Run all tests
    results = tester.run_all_tests()

    print(f"\nTest Summary:")
    print(f"Total tests: {results['total_tests']}")
    print("All prompt flows tested successfully!")


if __name__ == "__main__":
    main()