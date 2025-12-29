"""
Hallucination Prevention Module

This module implements advanced techniques to prevent hallucinations
in the RAG system by refining prompts and validation mechanisms.
"""
from typing import Dict, Any, List, Optional
from .prompt_templates import PromptBuilder, QueryMode
from .refusal_handler import RefusalHandler, RefusalType
from .constitution_enforcer import ConstitutionEnforcer
import re


class HallucinationPrevention:
    """
    Advanced hallucination prevention for the RAG system
    """

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.refusal_handler = RefusalHandler()
        self.constitution_enforcer = ConstitutionEnforcer()
        self.hallucination_patterns = [
            r"according to my training data",
            r"i know that",
            r"from general knowledge",
            r"i understand that",
            r"most likely",
            r"probably",
            r"perhaps",
            r"maybe",
            r"could be",
            r"might be",
            r"i think",
            r"in general",
            r"typically",
            r"usually",
            r"often",
            r"as you know",
            r"everyone knows",
            r"common knowledge",
            r"external sources",
            r"other places",
            r"elsewhere",
            r"additionally",
            r"furthermore",
            r"moreover"
        ]

    def enhance_system_prompt(self, base_system_prompt: str) -> str:
        """
        Enhance the system prompt with stronger anti-hallucination instructions
        """
        enhanced_prompt = base_system_prompt + """

        CRITICAL ANTI-HALLUCINATION RULES:
        1. NEVER use phrases like "according to my training data", "from general knowledge", "I think", "probably", etc.
        2. NEVER reference information not explicitly provided in the CONTEXT
        3. NEVER make up facts, figures, or details not present in the CONTEXT
        4. If the CONTEXT does not contain the answer, explicitly state this limitation
        5. NEVER provide external links, resources, or information not in the book
        6. Always ground your response in specific content from the CONTEXT
        7. When uncertain, refuse to answer rather than guessing

        Remember: Your knowledge is limited to the provided CONTEXT. Do not exceed these boundaries.
        """

        return enhanced_prompt

    def create_stronger_refusal_prompt(self, context: str, question: str) -> str:
        """
        Create a prompt that strongly emphasizes refusal when context is insufficient
        """
        return f"""Given the following context from the book:

CONTEXT:
{context}

QUESTION: {question}

If the context does not contain sufficient information to answer the question with high confidence, you MUST explicitly refuse to answer and state that the book content does not contain the necessary information. Do not attempt to answer from general knowledge or make up information.

Answer:"""

    def validate_response_for_hallucinations(self, response: str, context: str) -> Dict[str, Any]:
        """
        Validate a response for potential hallucinations
        """
        validation_result = {
            "is_valid": True,
            "hallucination_detected": False,
            "issues": [],
            "confidence_score": 1.0
        }

        response_lower = response.lower()

        # Check for hallucination patterns
        detected_patterns = []
        for pattern in self.hallucination_patterns:
            if re.search(pattern, response_lower):
                detected_patterns.append(pattern)

        if detected_patterns:
            validation_result["hallucination_detected"] = True
            validation_result["issues"].extend(detected_patterns)
            validation_result["is_valid"] = False

        # Check if response contains information not in context
        if context and response:
            # Simple semantic check: look for key terms
            context_words = set(context.lower().split())
            response_sentences = response.split('.')

            for sentence in response_sentences:
                sentence_words = set(sentence.lower().split())
                # If a sentence has no overlap with context, it might be hallucinated
                if len(sentence_words) > 5:  # Only check longer sentences
                    overlap = sentence_words.intersection(context_words)
                    if len(overlap) == 0:
                        validation_result["issues"].append(f"Potential hallucination: '{sentence.strip()[:100]}...'")
                        validation_result["hallucination_detected"] = True
                        validation_result["is_valid"] = False

        # Calculate confidence based on issues found
        issue_count = len(validation_result["issues"])
        validation_result["confidence_score"] = max(0.0, 1.0 - (issue_count * 0.1))

        return validation_result

    def refine_response(self, response: str, context: str) -> str:
        """
        Refine a response to remove potential hallucinations
        """
        # Remove common hallucination phrases
        refined_response = response

        for pattern in self.hallucination_patterns:
            # Remove sentences containing hallucination patterns
            sentences = refined_response.split('.')
            filtered_sentences = []

            for sentence in sentences:
                if not re.search(pattern, sentence.lower()):
                    filtered_sentences.append(sentence.strip())

            refined_response = '. '.join(filtered_sentences)

        # Ensure response is grounded in context
        if not self._response_is_contextually_valid(refined_response, context):
            # If the response isn't properly grounded, return a refusal
            return self.refusal_handler.get_refusal_message(RefusalType.INSUFFICIENT_CONTEXT)

        return refined_response

    def _response_is_contextually_valid(self, response: str, context: str) -> bool:
        """
        Check if a response is properly grounded in the context
        """
        if not context or not response:
            return False

        # Check for basic semantic alignment
        response_words = set(response.lower().split())
        context_words = set(context.lower().split())

        # Calculate overlap
        common_words = response_words.intersection(context_words)
        if len(common_words) == 0:
            return False

        # If at least 30% of response words are in context, consider it valid
        overlap_ratio = len(common_words) / len(response_words)
        return overlap_ratio >= 0.3

    def get_enhanced_prompt_parts(self, mode: QueryMode, context: str, question: str) -> Dict[str, str]:
        """
        Get enhanced prompt parts with stronger anti-hallucination measures
        """
        base_prompts = self.prompt_builder.build_book_scope_prompt(context, question) if mode == QueryMode.BOOK_SCOPE else self.prompt_builder.build_selected_text_prompt(context, question)

        # Enhance the system prompt
        enhanced_system = self.enhance_system_prompt(base_prompts["system"])

        return {
            "system": enhanced_system,
            "user": base_prompts["user"]
        }

    def run_hallucination_prevention_pipeline(self, query: str, context: str, response: str) -> Dict[str, Any]:
        """
        Run the complete hallucination prevention pipeline
        """
        pipeline_result = {
            "original_response": response,
            "validation": self.validate_response_for_hallucinations(response, context),
            "refined_response": None,
            "needs_refusal": False
        }

        if pipeline_result["validation"]["hallucination_detected"]:
            # If hallucinations detected, either refine or issue refusal
            refined = self.refine_response(response, context)
            pipeline_result["refined_response"] = refined

            # If refinement still has issues, issue refusal
            if refined != response:
                refined_validation = self.validate_response_for_hallucinations(refined, context)
                if refined_validation["hallucination_detected"]:
                    pipeline_result["needs_refusal"] = True
                    pipeline_result["refined_response"] = self.refusal_handler.get_refusal_message(RefusalType.HALLUCINATION_PREVENTION)
        else:
            pipeline_result["refined_response"] = response

        return pipeline_result

    def test_hallucination_prevention(self) -> Dict[str, Any]:
        """
        Test the hallucination prevention mechanisms
        """
        print("Testing Hallucination Prevention...")

        # Test cases with potential hallucinations
        test_cases = [
            {
                "name": "Response with general knowledge",
                "context": "ROS 2 is a robotics framework.",
                "response": "ROS 2 is a robotics framework. According to my training data, it was developed by Open Robotics. It's commonly used in industry.",
                "should_detect": True
            },
            {
                "name": "Properly grounded response",
                "context": "ROS 2 is a robotics framework developed by Open Robotics.",
                "response": "Based on the provided context, ROS 2 is a robotics framework developed by Open Robotics.",
                "should_detect": False
            },
            {
                "name": "Response with uncertainty phrases",
                "context": "ROS 2 is a robotics framework.",
                "response": "ROS 2 is a robotics framework. It might be used in various applications, and probably has many features.",
                "should_detect": True
            }
        ]

        results = []
        for test_case in test_cases:
            validation = self.validate_response_for_hallucinations(
                test_case["response"],
                test_case["context"]
            )

            result = {
                "test_name": test_case["name"],
                "should_detect": test_case["should_detect"],
                "actually_detected": validation["hallucination_detected"],
                "correct_detection": test_case["should_detect"] == validation["hallucination_detected"],
                "issues_found": validation["issues"]
            }

            results.append(result)
            print(f"  {test_case['name']}: {'PASS' if result['correct_detection'] else 'FAIL'}")

        return {
            "test_cases": results,
            "total_tests": len(results),
            "passed_tests": sum(1 for r in results if r["correct_detection"]),
            "pass_rate": sum(1 for r in results if r["correct_detection"]) / len(results) if results else 0
        }


def main():
    # Initialize the hallucination prevention system
    prevention = HallucinationPrevention()

    print("Hallucination Prevention System")
    print("=" * 40)

    # Test the hallucination prevention
    test_results = prevention.test_hallucination_prevention()

    print(f"\nHallucination Prevention Test Results:")
    print(f"  Passed: {test_results['passed_tests']}/{test_results['total_tests']}")
    print(f"  Pass rate: {test_results['pass_rate']:.1%}")

    # Example of enhanced prompt
    context = "ROS 2 is a flexible framework for developing robot applications."
    question = "What is ROS 2?"

    enhanced_prompts = prevention.get_enhanced_prompt_parts(QueryMode.BOOK_SCOPE, context, question)
    print(f"\nEnhanced system prompt length: {len(enhanced_prompts['system'])} characters")

    print(f"\nHallucination prevention system ready!")


if __name__ == "__main__":
    main()