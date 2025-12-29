"""
Deterministic Behavior Tester Module

This module tests that the RAG system produces consistent, deterministic
behavior across repeated runs with identical inputs.
"""
import time
import hashlib
from typing import Dict, Any, List, Optional
from .retriever import BookContentRetriever
from .min_text_retriever import MinimumTextRetriever
from .prompt_templates import PromptBuilder, QueryMode
import os


class DeterministicTester:
    """
    Tests deterministic behavior of the RAG system
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv('NEON_DB_URL')
        self.retriever = BookContentRetriever(self.db_url) if self.db_url else None
        self.min_text_retriever = MinimumTextRetriever(self.db_url) if self.db_url else None
        self.prompt_builder = PromptBuilder()

        if self.retriever:
            self.retriever.connect_to_db()
        if self.min_text_retriever:
            self.min_text_retriever.connect_to_db()

    def test_retrieval_consistency(self, query: str, num_runs: int = 5) -> Dict[str, Any]:
        """
        Test that retrieval produces consistent results across runs
        """
        print(f"Testing retrieval consistency for query: '{query[:50]}...' ({num_runs} runs)")

        results = []
        start_time = time.time()

        for i in range(num_runs):
            try:
                # Perform the same search multiple times
                search_results = self.retriever.search_content(query, limit=3) if self.retriever else []
                result_hash = hashlib.md5(str(search_results).encode()).hexdigest()

                results.append({
                    "run": i + 1,
                    "result_count": len(search_results) if search_results else 0,
                    "result_hash": result_hash,
                    "results": search_results
                })
            except Exception as e:
                results.append({
                    "run": i + 1,
                    "error": str(e),
                    "result_hash": None
                })

        end_time = time.time()

        # Check consistency
        hashes = [r["result_hash"] for r in results if r["result_hash"]]
        all_consistent = len(set(hashes)) <= 1 if hashes else False

        # Calculate timing statistics
        timing_stats = {
            "total_time": end_time - start_time,
            "avg_time_per_run": (end_time - start_time) / num_runs if num_runs > 0 else 0
        }

        result = {
            "test": "retrieval_consistency",
            "query": query,
            "num_runs": num_runs,
            "all_consistent": all_consistent,
            "result_hashes": hashes,
            "timing_stats": timing_stats,
            "individual_results": results,
            "success_rate": sum(1 for r in results if "error" not in r) / len(results)
        }

        print(f"  All runs consistent: {result['all_consistent']}")
        print(f"  Success rate: {result['success_rate']:.1%}")
        print(f"  Total time: {timing_stats['total_time']:.3f}s")

        return result

    def test_minimum_text_retrieval_consistency(self, query: str, selected_text: Optional[str] = None, num_runs: int = 3) -> Dict[str, Any]:
        """
        Test that minimum text retrieval produces consistent results
        """
        print(f"\nTesting minimum text retrieval consistency for query: '{query[:50]}...'")

        results = []

        for i in range(num_runs):
            try:
                if selected_text:
                    # Test selected text mode
                    retrieval_result = self.min_text_retriever.retrieve_for_selected_text_only(
                        selected_text, query
                    )
                else:
                    # Test book scope mode
                    retrieval_result = self.min_text_retriever.retrieve_for_book_scope(
                        query
                    )

                result_hash = hashlib.md5(str(retrieval_result).encode()).hexdigest()

                results.append({
                    "run": i + 1,
                    "context_length": len(retrieval_result.get('context', '')),
                    "token_count": retrieval_result.get('token_count', 0),
                    "is_sufficient": retrieval_result.get('is_sufficient', False),
                    "result_hash": result_hash
                })
            except Exception as e:
                results.append({
                    "run": i + 1,
                    "error": str(e),
                    "result_hash": None
                })

        # Check consistency
        hashes = [r["result_hash"] for r in results if r["result_hash"]]
        all_consistent = len(set(hashes)) <= 1 if hashes else False

        result = {
            "test": "minimum_text_retrieval_consistency",
            "query": query,
            "selected_text_provided": selected_text is not None,
            "num_runs": num_runs,
            "all_consistent": all_consistent,
            "result_hashes": hashes,
            "individual_results": results,
            "success_rate": sum(1 for r in results if "error" not in r) / len(results)
        }

        print(f"  All runs consistent: {result['all_consistent']}")
        print(f"  Success rate: {result['success_rate']:.1%}")

        return result

    def test_prompt_generation_consistency(self, mode: QueryMode, context: str, question: str, num_runs: int = 5) -> Dict[str, Any]:
        """
        Test that prompt generation is consistent
        """
        print(f"\nTesting prompt generation consistency for mode: {mode.value}")

        results = []

        for i in range(num_runs):
            try:
                if mode == QueryMode.BOOK_SCOPE:
                    prompt_parts = self.prompt_builder.build_book_scope_prompt(context, question)
                else:
                    prompt_parts = self.prompt_builder.build_selected_text_prompt(context, question)

                system_hash = hashlib.md5(prompt_parts["system"].encode()).hexdigest()
                user_hash = hashlib.md5(prompt_parts["user"].encode()).hexdigest()

                results.append({
                    "run": i + 1,
                    "system_hash": system_hash,
                    "user_hash": user_hash,
                    "system_length": len(prompt_parts["system"]),
                    "user_length": len(prompt_parts["user"])
                })
            except Exception as e:
                results.append({
                    "run": i + 1,
                    "error": str(e),
                    "system_hash": None,
                    "user_hash": None
                })

        # Check consistency
        system_hashes = [r["system_hash"] for r in results if r["system_hash"]]
        user_hashes = [r["user_hash"] for r in results if r["user_hash"]]

        system_consistent = len(set(system_hashes)) <= 1 if system_hashes else False
        user_consistent = len(set(user_hashes)) <= 1 if user_hashes else False
        all_consistent = system_consistent and user_consistent

        result = {
            "test": "prompt_generation_consistency",
            "mode": mode.value,
            "num_runs": num_runs,
            "system_consistent": system_consistent,
            "user_consistent": user_consistent,
            "all_consistent": all_consistent,
            "system_hashes": system_hashes,
            "user_hashes": user_hashes,
            "individual_results": results,
            "success_rate": sum(1 for r in results if "error" not in r) / len(results)
        }

        print(f"  System prompt consistent: {result['system_consistent']}")
        print(f"  User prompt consistent: {result['user_consistent']}")
        print(f"  All consistent: {result['all_consistent']}")

        return result

    def test_complete_flow_consistency(self, query: str, selected_text: Optional[str] = None, num_runs: int = 3) -> Dict[str, Any]:
        """
        Test consistency of the complete flow (retrieval + prompt generation)
        """
        print(f"\nTesting complete flow consistency for query: '{query[:50]}...'")

        results = []

        for i in range(num_runs):
            try:
                # Step 1: Retrieve context
                if selected_text:
                    # Selected text mode
                    mode = QueryMode.SELECTED_TEXT_ONLY
                    context_result = self.min_text_retriever.retrieve_for_selected_text_only(
                        selected_text, query
                    )
                else:
                    # Book scope mode
                    mode = QueryMode.BOOK_SCOPE
                    context_result = self.min_text_retriever.retrieve_for_book_scope(query)

                # Step 2: Generate prompt
                if mode == QueryMode.BOOK_SCOPE:
                    prompt_parts = self.prompt_builder.build_book_scope_prompt(
                        context_result['context'], query
                    )
                else:
                    prompt_parts = self.prompt_builder.build_selected_text_prompt(
                        context_result['context'], query
                    )

                # Create a hash of the complete flow result
                flow_data = {
                    "context": context_result['context'],
                    "system_prompt": prompt_parts["system"],
                    "user_prompt": prompt_parts["user"]
                }
                flow_hash = hashlib.md5(str(flow_data).encode()).hexdigest()

                results.append({
                    "run": i + 1,
                    "context_hash": hashlib.md5(context_result['context'].encode()).hexdigest(),
                    "system_hash": hashlib.md5(prompt_parts["system"].encode()).hexdigest(),
                    "user_hash": hashlib.md5(prompt_parts["user"].encode()).hexdigest(),
                    "flow_hash": flow_hash,
                    "context_length": len(context_result['context']),
                    "context_sufficient": context_result['is_sufficient']
                })
            except Exception as e:
                results.append({
                    "run": i + 1,
                    "error": str(e),
                    "flow_hash": None
                })

        # Check consistency
        flow_hashes = [r["flow_hash"] for r in results if r["flow_hash"]]
        all_consistent = len(set(flow_hashes)) <= 1 if flow_hashes else False

        result = {
            "test": "complete_flow_consistency",
            "query": query,
            "selected_text_provided": selected_text is not None,
            "num_runs": num_runs,
            "all_consistent": all_consistent,
            "flow_hashes": flow_hashes,
            "individual_results": results,
            "success_rate": sum(1 for r in results if "error" not in r) / len(results)
        }

        print(f"  Complete flow consistent: {result['all_consistent']}")
        print(f"  Success rate: {result['success_rate']:.1%}")

        return result

    def run_deterministic_tests(self) -> Dict[str, Any]:
        """
        Run all deterministic behavior tests
        """
        print("Running deterministic behavior tests...\n")

        # Sample test data
        test_query = "What is ROS 2?"
        test_context = "ROS 2 is a flexible framework for developing robot applications. It provides a collection of libraries and tools that help developers create robot applications."
        test_selected_text = "ROS 2 is designed for large development efforts."

        test_results = {
            "retrieval_consistency": self.test_retrieval_consistency(test_query, 3),
            "minimum_text_retrieval": self.test_minimum_text_retrieval_consistency(test_query, None, 3),
            "selected_text_retrieval": self.test_minimum_text_retrieval_consistency(test_query, test_selected_text, 3),
            "prompt_generation_book_scope": self.test_prompt_generation_consistency(QueryMode.BOOK_SCOPE, test_context, test_query, 3),
            "prompt_generation_selected_text": self.test_prompt_generation_consistency(QueryMode.SELECTED_TEXT_ONLY, test_selected_text, test_query, 3),
            "complete_flow_book_scope": self.test_complete_flow_consistency(test_query, None, 3),
            "complete_flow_selected_text": self.test_complete_flow_consistency(test_query, test_selected_text, 3)
        }

        # Calculate summary
        total_tests = len(test_results)
        consistent_tests = sum(1 for result in test_results.values() if result["all_consistent"])
        success_rate = sum(result["success_rate"] for result in test_results.values()) / total_tests

        summary = {
            "total_tests": total_tests,
            "consistent_tests": consistent_tests,
            "inconsistent_tests": total_tests - consistent_tests,
            "consistency_rate": consistent_tests / total_tests if total_tests > 0 else 0,
            "average_success_rate": success_rate,
            "all_results": test_results,
            "system_deterministic": consistent_tests == total_tests and success_rate >= 0.95  # 95% success rate
        }

        print(f"\nDeterministic Behavior Test Summary:")
        print(f"  Consistent tests: {summary['consistent_tests']}/{summary['total_tests']}")
        print(f"  Consistency rate: {summary['consistency_rate']:.1%}")
        print(f"  Average success rate: {summary['average_success_rate']:.1%}")
        print(f"  System is deterministic: {summary['system_deterministic']}")

        return summary


def main():
    # Initialize the deterministic tester
    tester = DeterministicTester()

    print("Deterministic Behavior Tester")
    print("=" * 50)

    # Run all tests
    results = tester.run_deterministic_tests()

    print(f"\nDeterministic testing complete!")
    print(f"System deterministic: {results['system_deterministic']}")

    if results['system_deterministic']:
        print("✅ System demonstrates consistent, deterministic behavior across repeated runs!")
    else:
        print("⚠️  Some tests showed inconsistent behavior that may need investigation.")


if __name__ == "__main__":
    main()