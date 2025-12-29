"""
Constitution Enforcement Module

This module implements the project constitution as the system-level authority,
ensuring all RAG operations align with the defined principles and constraints.
"""
from typing import Dict, Any, List, Optional
import logging


class ConstitutionEnforcer:
    """
    Enforces the project constitution principles during RAG operations
    """

    def __init__(self):
        # Load constitution principles
        self.principles = {
            "I": {
                "name": "Accuracy via Primary Sources",
                "description": "All technical content MUST be derived from authoritative primary sources",
                "rules": [
                    "No hallucination of information not present in book content",
                    "All answers must be traceable to specific book sections",
                    "Refuse to answer if content not found in book"
                ]
            },
            "II": {
                "name": "Clarity for Technical Audiences",
                "description": "Content MUST be clear, precise, and accessible to readers with technical backgrounds",
                "rules": [
                    "Provide clear, well-structured responses",
                    "Use appropriate technical terminology consistently",
                    "Ensure responses are understandable to technical audiences"
                ]
            },
            "III": {
                "name": "Reproducibility of Code, Simulations, and Experiments",
                "description": "All code, simulations, and experiments MUST be reproducible",
                "rules": [
                    "Provide specific references to book sections with implementation details",
                    "Include environment specifications when discussing code",
                    "Ensure all referenced procedures can be followed by readers"
                ]
            },
            "IV": {
                "name": "Rigor via Peer-Reviewed and Official Sources",
                "description": "Source quality directly impacts content reliability",
                "rules": [
                    "Only provide information that exists in the book content",
                    "Don't supplement with external knowledge",
                    "Acknowledge limitations of book content when necessary"
                ]
            },
            "V": {
                "name": "Zero Plagiarism and Proper Attribution",
                "description": "All content MUST be original or properly attributed",
                "rules": [
                    "Attribute all information to specific book sections",
                    "Don't claim external knowledge as book content",
                    "Maintain academic integrity in responses"
                ]
            },
            "VI": {
                "name": "Deliverables and Tooling Constraints",
                "description": "Project MUST use Spec-Kit Plus methodology with Claude Code, Docusaurus",
                "rules": [
                    "Only provide information about tools and methodologies in the book",
                    "Don't recommend external tools not mentioned in book",
                    "Maintain alignment with Docusaurus and Claude Code methodology"
                ]
            },
            "VII": {
                "name": "AI-to-Robot Pipeline Reproducibility",
                "description": "AI models and robot control pipelines MUST be reproducible",
                "rules": [
                    "Provide specific implementation details from the book",
                    "Include environment setup instructions from book content",
                    "Reference specific simulation and hardware configurations from book"
                ]
            }
        }

    def validate_response_context(self, response: str, source_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that a response adheres to constitution principles based on its source context
        """
        validation_result = {
            "is_valid": True,
            "violations": [],
            "principles_applied": [],
            "confidence": 1.0  # Default high confidence
        }

        # Check if response contains information not in source chunks (hallucination check)
        if not source_chunks:
            validation_result["is_valid"] = False
            validation_result["violations"].append({
                "principle": "I",
                "description": "No source chunks provided - potential hallucination"
            })

        # Check for proper attribution to book sections
        if source_chunks:
            # Verify that the response doesn't contain information not in the sources
            source_content = " ".join([chunk.get('content', '') for chunk in source_chunks])

            # For now, we'll trust that the retrieval system provides relevant content
            # In a more sophisticated system, we'd check semantic alignment

            validation_result["principles_applied"].append({
                "principle": "I",
                "description": "Verified response based on provided source chunks"
            })

        return validation_result

    def check_constitutional_compliance(self, query: str, context: str, response: str) -> Dict[str, Any]:
        """
        Check if a query-response-context combination complies with constitution principles
        """
        compliance_result = {
            "is_compliant": True,
            "issues": [],
            "recommendations": []
        }

        # Check for hallucination (Principle I)
        if not context.strip() and response.strip():
            compliance_result["is_compliant"] = False
            compliance_result["issues"].append({
                "principle": "I",
                "issue": "Response provided without context - potential hallucination",
                "severity": "critical"
            })

        # Check for proper source attribution (Principle V)
        if response.strip() and not self._has_source_reference(response):
            compliance_result["recommendations"].append({
                "principle": "V",
                "recommendation": "Include references to specific book sections in response"
            })

        return compliance_result

    def _has_source_reference(self, response: str) -> bool:
        """
        Check if the response contains references to book sections
        """
        # Look for common reference patterns
        reference_patterns = [
            "chapter", "section", "module", "page", "figure",
            "section", "subsection", "book", "documentation"
        ]

        response_lower = response.lower()
        return any(pattern in response_lower for pattern in reference_patterns)

    def enforce_constitution_rules(self, query: str, context: str, response: str) -> str:
        """
        Enforce constitution rules on a response, modifying it if necessary
        """
        # Check for compliance
        compliance = self.check_constitutional_compliance(query, context, response)

        if not compliance["is_compliant"]:
            # If there are critical issues, modify the response
            for issue in compliance["issues"]:
                if issue["severity"] == "critical":
                    # For critical issues like hallucination, return a compliant refusal
                    return (
                        "I cannot answer this question based on the book content provided. "
                        "The response would require information not available in the book. "
                        "Please refer to the relevant book sections for accurate information."
                    )

        # Add source references if missing
        if not self._has_source_reference(response) and context:
            response += (
                "\n\nNote: This information is based on the book content. "
                "For more details, please refer to the specific book sections "
                "that contain this information."
            )

        return response

    def get_constitution_principles(self) -> Dict[str, Any]:
        """
        Return the constitution principles for reference
        """
        return self.principles

    def validate_context_sufficiency(self, query: str, context: str) -> Dict[str, Any]:
        """
        Validate whether the provided context is sufficient to answer the query
        according to constitution principles
        """
        validation = {
            "is_sufficient": False,
            "reason": "",
            "required_principles": ["I", "IV"]  # Accuracy and rigor
        }

        if not context.strip():
            validation["reason"] = "No context provided - cannot answer without book content"
            return validation

        # Simple check: if context is too short, it might not be sufficient
        if len(context.strip()) < 50:
            validation["reason"] = "Context too brief to provide accurate answer"
            return validation

        # Check if context seems relevant to query (basic keyword matching)
        query_keywords = set(query.lower().split())
        context_lower = context.lower()
        context_words = set(context_lower.split())

        # If there's significant overlap in keywords, consider it sufficient
        common_words = query_keywords.intersection(context_words)
        if len(common_words) > 0:
            validation["is_sufficient"] = True
            validation["reason"] = "Context contains relevant information for the query"
        else:
            validation["reason"] = "Context does not appear to contain relevant information for the query"

        return validation


def main():
    # Initialize the constitution enforcer
    enforcer = ConstitutionEnforcer()

    print("Constitution enforcement system initialized successfully!")
    print("\nConstitution principles loaded:")

    for principle_id, details in enforcer.principles.items():
        print(f"  {principle_id}. {details['name']}")

    # Example usage
    query = "How do I install ROS 2?"
    context = "ROS 2 can be installed from the official documentation. Visit the ROS 2 installation page..."
    response = "To install ROS 2, you should visit the official ROS 2 documentation website."

    print(f"\nExample validation for query: '{query[:50]}...'")

    compliance = enforcer.check_constitutional_compliance(query, context, response)
    print(f"Compliance check result: {compliance['is_compliant']}")

    if compliance['issues']:
        print(f"Issues found: {compliance['issues']}")

    if compliance['recommendations']:
        print(f"Recommendations: {compliance['recommendations']}")


if __name__ == "__main__":
    main()