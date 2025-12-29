"""
Reader Response Validator Module

This module validates that reader-facing responses are clear,
accurate, and faithful to the source content.
"""
import re
from typing import Dict, Any, List
from .retriever import BookContentRetriever
from .min_text_retriever import MinimumTextRetriever
from .refusal_handler import RefusalHandler
import os


class ResponseValidator:
    """
    Validates reader-facing responses for clarity and fidelity
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv('NEON_DB_URL')
        self.retriever = BookContentRetriever(self.db_url) if self.db_url else None
        self.min_text_retriever = MinimumTextRetriever(self.db_url) if self.db_url else None
        self.refusal_handler = RefusalHandler()

        if self.retriever:
            self.retriever.connect_to_db()
        if self.min_text_retriever:
            self.min_text_retriever.connect_to_db()

    def validate_clarity(self, response: str) -> Dict[str, Any]:
        """
        Validate that the response is clear and understandable
        """
        clarity_metrics = {
            "length": len(response),
            "word_count": len(response.split()),
            "sentence_count": len(re.split(r'[.!?]+', response)),
            "avg_sentence_length": 0,
            "has_unclear_phrases": False,
            "readability_score": 0
        }

        if clarity_metrics["sentence_count"] > 0:
            clarity_metrics["avg_sentence_length"] = clarity_metrics["word_count"] / clarity_metrics["sentence_count"]

        # Check for unclear phrases
        unclear_patterns = [
            r"maybe",
            r"perhaps",
            r"possibly",
            r"i think",
            r"i believe",
            r"probably",
            r"likely",
            r"sort of",
            r"kinda",
            r"not sure",
            r"uncertain"
        ]

        response_lower = response.lower()
        unclear_matches = []
        for pattern in unclear_patterns:
            if re.search(pattern, response_lower):
                unclear_matches.append(pattern)

        clarity_metrics["has_unclear_phrases"] = len(unclear_matches) > 0
        clarity_metrics["unclear_phrases"] = unclear_matches

        # Simple readability score (higher is better clarity)
        clarity_score = 0
        clarity_score += 1 if 50 <= clarity_metrics["word_count"] <= 500 else 0  # Reasonable length
        clarity_score += 1 if clarity_metrics["avg_sentence_length"] <= 25 else 0  # Not too long sentences
        clarity_score += 1 if not clarity_metrics["has_unclear_phrases"] else 0  # Clear language
        clarity_score += 1 if clarity_metrics["sentence_count"] >= 1 else 0  # Has content

        clarity_metrics["readability_score"] = clarity_score / 4  # Normalize to 0-1

        result = {
            "is_clear": clarity_score >= 3,  # At least 3 out of 4 criteria met
            "clarity_score": clarity_score,
            "readability_score": clarity_metrics["readability_score"],
            "metrics": clarity_metrics
        }

        return result

    def validate_fidelity(self, response: str, source_context: str) -> Dict[str, Any]:
        """
        Validate that the response is faithful to the source context
        """
        if not source_context:
            # If no source context, check if response is a refusal
            is_refusal = any(phrase in response.lower() for phrase in [
                "cannot answer", "not in the book", "no context provided",
                "insufficient information", "not found in book content"
            ])
            return {
                "is_faithful": is_refusal,  # Refusals are faithful when no context
                "fidelity_score": 1.0 if is_refusal else 0.0,
                "issues": [] if is_refual else ["No source context provided for verification"],
                "confidence": 1.0 if is_refusal else 0.5
            }

        # Check for factual consistency
        response_lower = response.lower()
        context_lower = source_context.lower()

        # Look for contradictions
        contradictions = []
        positive_claims = re.findall(r'\b(ROS 2|robot|framework|application|library|tool)\b', response_lower)

        for claim in positive_claims:
            # Check if the claim exists in context
            if claim.lower() not in context_lower and len(claim) > 2:  # Skip short words
                contradictions.append(f"Claim '{claim}' not found in context")

        # Check for semantic alignment
        response_words = set(response_lower.split())
        context_words = set(context_lower.split())

        if len(response_words) > 0:
            overlap = len(response_words.intersection(context_words))
            alignment_score = overlap / len(response_words)
        else:
            alignment_score = 0

        # Check for hallucinated details
        hallucination_indicators = [
            "according to my training",
            "from external sources",
            "in general",
            "typically",
            "usually",
            "most sources",
            "commonly known"
        ]

        hallucinations = []
        for indicator in hallucination_indicators:
            if indicator in response_lower:
                hallucinations.append(indicator)

        fidelity_score = alignment_score
        if hallucinations:
            fidelity_score *= 0.5  # Penalize for hallucinations

        result = {
            "is_faithful": fidelity_score > 0.3 and len(hallucinations) == 0,  # Threshold and no hallucinations
            "fidelity_score": fidelity_score,
            "alignment_score": alignment_score,
            "issues": contradictions + hallucinations,
            "confidence": fidelity_score
        }

        return result

    def validate_reader_friendly(self, response: str) -> Dict[str, Any]:
        """
        Validate that the response is reader-friendly
        """
        # Check for professional tone
        unprofessional_phrases = [
            "idk", "dunno", "wtf", "lol", "haha", "jk", "tbh",
            "imo", "fyi", "afaik", "btw"
        ]

        unprofessional_matches = []
        response_lower = response.lower()
        for phrase in unprofessional_phrases:
            if phrase in response_lower:
                unprofessional_matches.append(phrase)

        # Check for proper structure
        has_structure = (
            response.count('\n') >= 1 or  # Has some formatting
            response.count(':') >= 1 or  # Has labels
            len(re.findall(r'\d+\.', response)) >= 1  # Has numbered items
        )

        # Check for helpfulness
        helpful_indicators = [
            "based on", "according to", "from the", "the book states",
            "as mentioned", "refers to", "describes", "explains"
        ]

        helpful_score = sum(1 for indicator in helpful_indicators if indicator in response_lower)
        is_helpful = helpful_score > 0

        result = {
            "is_reader_friendly": len(unprofessional_matches) == 0 and has_structure,
            "reader_friendly_score": 1.0 if len(unprofessional_matches) == 0 else 0.0,
            "has_good_structure": has_structure,
            "is_helpful": is_helpful,
            "unprofessional_phrases": unprofessional_matches
        }

        return result

    def validate_complete_response(self, response: str, source_context: str = "") -> Dict[str, Any]:
        """
        Perform complete validation of a response
        """
        clarity = self.validate_clarity(response)
        fidelity = self.validate_fidelity(response, source_context)
        reader_friendly = self.validate_reader_friendly(response)

        overall_score = (
            clarity["readability_score"] * 0.3 +
            fidelity["fidelity_score"] * 0.5 +
            (1.0 if reader_friendly["is_reader_friendly"] else 0.0) * 0.2
        )

        result = {
            "overall_valid": (
                clarity["is_clear"] and
                fidelity["is_faithful"] and
                reader_friendly["is_reader_friendly"]
            ),
            "overall_score": overall_score,
            "clarity_validation": clarity,
            "fidelity_validation": fidelity,
            "reader_friendly_validation": reader_friendly,
            "summary": {
                "clarity_pass": clarity["is_clear"],
                "fidelity_pass": fidelity["is_faithful"],
                "reader_friendly_pass": reader_friendly["is_reader_friendly"]
            }
        }

        return result

    def test_sample_responses(self) -> List[Dict[str, Any]]:
        """
        Test validation on sample responses
        """
        print("Testing response validation on sample responses...")

        test_cases = [
            {
                "name": "Good response",
                "response": "Based on the book content, ROS 2 is a flexible framework for developing robot applications. It provides libraries and tools for building robot software.",
                "context": "ROS 2 is a flexible framework for developing robot applications. It provides libraries and tools.",
                "expected_valid": True
            },
            {
                "name": "Refusal response",
                "response": "I cannot answer this question based on the provided book content. The information is not available in the book.",
                "context": "",
                "expected_valid": True
            },
            {
                "name": "Unclear response",
                "response": "Maybe ROS 2 is some kind of framework, possibly for robots, I think. Not sure about the details.",
                "context": "ROS 2 is a robotics framework.",
                "expected_valid": False
            },
            {
                "name": "Hallucinated response",
                "response": "Based on my training data, ROS 2 was developed by Open Robotics in 2010. According to general knowledge, it's widely used in industry.",
                "context": "ROS 2 is a robotics framework.",
                "expected_valid": False
            }
        ]

        results = []
        for test_case in test_cases:
            validation = self.validate_complete_response(
                test_case["response"],
                test_case["context"]
            )

            result = {
                "test_name": test_case["name"],
                "expected_valid": test_case["expected_valid"],
                "actually_valid": validation["overall_valid"],
                "correct": test_case["expected_valid"] == validation["overall_valid"],
                "overall_score": validation["overall_score"],
                "details": {
                    "clarity": validation["clarity_validation"]["is_clear"],
                    "fidelity": validation["fidelity_validation"]["is_faithful"],
                    "reader_friendly": validation["reader_friendly_validation"]["is_reader_friendly"]
                }
            }

            results.append(result)
            print(f"  {test_case['name']}: Expected {test_case['expected_valid']}, Got {validation['overall_valid']}, Correct: {result['correct']}")

        return results

    def validate_refusal_responses(self) -> Dict[str, Any]:
        """
        Specifically validate that refusal responses are appropriate
        """
        print("\nValidating refusal responses...")

        # Test various refusal messages
        refusal_messages = [
            self.refusal_handler.get_refusal_message(refusal_type)
            for refusal_type in self.refusal_handler.refusal_messages.keys()
        ]

        valid_refusals = 0
        for msg in refusal_messages:
            validation = self.validate_complete_response(msg)
            if validation["overall_valid"]:
                valid_refusals += 1

        result = {
            "total_refusal_messages": len(refusal_messages),
            "valid_refusals": valid_refusals,
            "refusal_validation_rate": valid_refusals / len(refusal_messages) if refusal_messages else 0,
            "all_refusals_valid": valid_refusals == len(refusal_messages)
        }

        print(f"  Valid refusals: {result['valid_refusals']}/{result['total_refusal_messages']}")
        print(f"  Validation rate: {result['refusal_validation_rate']:.1%}")

        return result

    def run_response_validation_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive response validation tests
        """
        print("Running comprehensive response validation tests...\n")

        sample_tests = self.test_sample_responses()
        refusal_tests = self.validate_refusal_responses()

        # Calculate overall results
        total_sample_tests = len(sample_tests)
        passed_sample_tests = sum(1 for test in sample_tests if test["correct"])

        summary = {
            "sample_tests": {
                "total": total_sample_tests,
                "passed": passed_sample_tests,
                "failed": total_sample_tests - passed_sample_tests,
                "pass_rate": passed_sample_tests / total_sample_tests if total_sample_tests > 0 else 0,
                "details": sample_tests
            },
            "refusal_tests": refusal_tests,
            "overall_validation_rate": (
                passed_sample_tests + (refusal_tests["valid_refusals"] if refusal_tests["total_refusal_messages"] > 0 else 0)
            ) / (
                total_sample_tests + refusal_tests["total_refusal_messages"] if total_sample_tests + refusal_tests["total_refusal_messages"] > 0 else 1
            ),
            "system_validates_well": passed_sample_tests / total_sample_tests >= 0.75 if total_sample_tests > 0 else False
        }

        print(f"\nResponse Validation Summary:")
        print(f"  Sample tests: {summary['sample_tests']['passed']}/{summary['sample_tests']['total']} passed ({summary['sample_tests']['pass_rate']:.1%})")
        print(f"  Refusal validation rate: {summary['refusal_tests']['refusal_validation_rate']:.1%}")
        print(f"  Overall validation rate: {summary['overall_validation_rate']:.1%}")
        print(f"  System validates well: {summary['system_validates_well']}")

        return summary


def main():
    # Initialize the response validator
    validator = ResponseValidator()

    print("Reader Response Validator")
    print("=" * 50)

    # Run comprehensive tests
    results = validator.run_response_validation_tests()

    print(f"\nResponse validation complete!")
    print(f"System validates responses well: {results['system_validates_well']}")

    if results['system_validates_well']:
        print("✅ Reader-facing responses are clear and faithful to source content!")
    else:
        print("⚠️  Some responses may need improvement for clarity or faithfulness.")


if __name__ == "__main__":
    main()