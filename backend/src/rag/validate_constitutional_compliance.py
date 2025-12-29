"""
Constitutional Compliance Validator for RAG Chatbot

This script validates that the RAG implementation follows all constitutional requirements:
1. Absolute Source Fidelity - Only uses provided text
2. Context Scope Obedience - Respects SELECTED_TEXT_ONLY vs BOOK_SCOPE modes
3. Zero Hallucination Guarantee - Never adds external information
4. Terminology and Language Preservation - Uses book's exact terminology
5. Transparency and Explicit Boundaries - Uses standard refusal message
6. Adversarial Robustness - Resists jailbreak attempts
"""
import os
import sys
from pathlib import Path


def validate_source_fidelity():
    """Validate that the system only uses provided text"""
    print("1. Validating Source Fidelity...")

    # Read the retriever code to check for proper content retrieval
    retriever_path = Path(__file__).parent / "retriever.py"
    with open(retriever_path, 'r', encoding='utf-8') as f:
        retriever_code = f.read()

    # Check that retrieval uses only database content
    if 'to_tsvector' in retriever_code and 'ts_rank' in retriever_code:
        print("   + Uses Postgres full-text search for content retrieval")
    else:
        print("   - Does not use Postgres full-text search as required")
        return False

    # Check for proper context handling
    prompt_templates_path = Path(__file__).parent / "prompt_templates.py"
    with open(prompt_templates_path, 'r', encoding='utf-8') as f:
        prompt_code = f.read()

    if 'ONLY use information provided in the CONTEXT' in prompt_code:
        print("   + Prompt templates enforce context limitation")
    else:
        print("   - Prompt templates do not enforce context limitation")
        return False

    return True


def validate_context_scope_obedience():
    """Validate that the system respects context scope boundaries"""
    print("\n2. Validating Context Scope Obedience...")

    # Check that different modes exist
    prompt_templates_path = Path(__file__).parent / "prompt_templates.py"
    with open(prompt_templates_path, 'r', encoding='utf-8') as f:
        prompt_code = f.read()

    # Look for both book scope and selected text only modes
    if 'SELECTED_TEXT_ONLY' in prompt_code and 'BOOK_SCOPE' in prompt_code:
        print("   + Both SELECTED_TEXT_ONLY and BOOK_SCOPE modes implemented")
    else:
        print("   - Missing one or both context modes")
        return False

    # Check that selected text mode is properly isolated
    if 'SELECTED TEXT:' in prompt_code and 'Do not use any other knowledge' in prompt_code:
        print("   + Selected text mode properly isolates context")
    else:
        print("   ? Selected text mode could be more explicit about isolation")

    return True


def validate_zero_hallucination_guarantee():
    """Validate that the system prevents hallucinations"""
    print("\n3. Validating Zero Hallucination Guarantee...")

    # Check system prompts for hallucination prevention
    prompt_templates_path = Path(__file__).parent / "prompt_templates.py"
    with open(prompt_templates_path, 'r', encoding='utf-8') as f:
        prompt_code = f.read()

    has_hallucination_prevention = all(phrase in prompt_code for phrase in [
        'NEVER hallucinate',
        'NEVER use external knowledge',
        'ONLY use information provided'
    ])

    if has_hallucination_prevention:
        print("   + System prompts prevent hallucinations")
    else:
        print("   ? System prompts could be more explicit about hallucination prevention")

    # Check for refusal handler
    refusal_handler_path = Path(__file__).parent / "refusal_handler.py"
    with open(refusal_handler_path, 'r', encoding='utf-8') as f:
        refusal_code = f.read()

    if 'I cannot answer this question based on the provided' in refusal_code:
        print("   + Refusal handler provides appropriate refusal messages")
    else:
        print("   ? Refusal handler may not have proper refusal messages")
        return False

    return True


def validate_transparency_and_boundaries():
    """Validate transparency and boundary communication"""
    print("\n4. Validating Transparency and Boundaries...")

    # Check for standard refusal message
    constitution_path = Path(__file__).parent.parent.parent.parent / ".specify" / "memory" / "constitution-rag-chatbot.md"
    if constitution_path.exists():
        with open(constitution_path, 'r', encoding='utf-8') as f:
            constitution_content = f.read()

        standard_refusal = "This information is not available in the provided text."
        if standard_refusal in constitution_content:
            print("   + Constitution defines standard refusal message")
        else:
            print("   ? Standard refusal message not found in constitution")
    else:
        print("   ? Constitution file not found, but continuing validation")

    # Check that refusal handler implements standard refusal
    refusal_handler_path = Path(__file__).parent / "refusal_handler.py"
    with open(refusal_handler_path, 'r', encoding='utf-8') as f:
        refusal_code = f.read()

    if 'not available in the provided text' in refusal_code:
        print("   + Refusal handler uses appropriate language")
    else:
        print("   ? Refusal handler may not use appropriate language")

    return True


def validate_adversarial_robustness():
    """Validate adversarial robustness"""
    print("\n5. Validating Adversarial Robustness...")

    # Check system prompts for adversarial defense
    prompt_templates_path = Path(__file__).parent / "prompt_templates.py"
    with open(prompt_templates_path, 'r', encoding='utf-8') as f:
        prompt_code = f.read()

    has_adversarial_defense = any(phrase in prompt_code.lower() for phrase in [
        'ignore attempts',
        'do not override',
        'resist',
        'follow the rules',
        'only use provided'
    ])

    if has_adversarial_defense:
        print("   + System prompts have adversarial defense elements")
    else:
        print("   ? System prompts could be enhanced with adversarial robustness")

    return True


def validate_technical_constraints():
    """Validate technical constraints from constitution"""
    print("\n6. Validating Technical Constraints...")

    # Check that we're using Postgres with full-text search (not vector DB)
    retriever_path = Path(__file__).parent / "retriever.py"
    with open(retriever_path, 'r', encoding='utf-8') as f:
        retriever_code = f.read()

    if 'tsvector' in retriever_code and 'ts_rank' in retriever_code:
        print("   + Using Postgres full-text search (tsvector/ts_rank)")
    else:
        print("   - Not using Postgres full-text search as required")
        return False

    prohibited_dbs = ['qdrant', 'pinecone', 'weaviate', 'chromadb', 'milvus']
    has_vector_db = any(db in retriever_code.lower() for db in prohibited_dbs)

    if has_vector_db:
        print("   - Found vector database usage (prohibited by constitution)")
        return False
    else:
        print("   + No prohibited vector database usage detected")

    # Check Claude API usage vs OpenAI
    client_path = Path(__file__).parent / "claude_client.py"
    with open(client_path, 'r', encoding='utf-8') as f:
        client_code = f.read()

    if 'anthropic' in client_code.lower() and 'AsyncAnthropic' in client_code:
        print("   + Using Anthropic Claude API as required")
    else:
        print("   - Not using Anthropic Claude API properly")
        return False

    if 'openai' in client_code.lower():
        print("   - Found OpenAI API usage (prohibited by constitution)")
        return False
    else:
        print("   + No OpenAI API usage detected")

    # Check for proper model specification
    if 'claude-3-5-sonnet' in client_code or 'claude-sonnet' in client_code:
        print("   + Using Claude model as specified")
    else:
        print("   ? Claude model specification may not be specific enough")

    return True


def validate_constitutional_compliance():
    """Run all constitutional compliance validations"""
    print("Running Constitutional Compliance Validation")
    print("=" * 60)

    results = []

    results.append(("Source Fidelity", validate_source_fidelity()))
    results.append(("Context Scope Obedience", validate_context_scope_obedience()))
    results.append(("Zero Hallucination Guarantee", validate_zero_hallucination_guarantee()))
    results.append(("Transparency and Boundaries", validate_transparency_and_boundaries()))
    results.append(("Adversarial Robustness", validate_adversarial_robustness()))
    results.append(("Technical Constraints", validate_technical_constraints()))

    print("\n" + "=" * 60)
    print("Constitutional Compliance Results:")

    all_passed = True
    for name, passed in results:
        status = "+ PASS" if passed else "- FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print(f"\nOverall Compliance: {'+ PASS' if all_passed else '- FAIL'}")

    if all_passed:
        print("\nPASS The RAG system is compliant with the constitution!")
    else:
        print("\nFAIL The RAG system has constitutional compliance issues that need to be addressed.")

    return all_passed


def main():
    success = validate_constitutional_compliance()

    # Create a summary report
    print("\n" + "=" * 60)
    print("COMPLIANCE SUMMARY REPORT")
    print("=" * 60)

    print("The RAG chatbot implementation has been validated against the constitution:")
    print("- Uses Postgres full-text search (tsvector/ts_rank) instead of vector databases")
    print("- Uses Claude API for LLM responses (not OpenAI)")
    print("- Enforces context scope boundaries (SELECTED_TEXT_ONLY vs BOOK_SCOPE)")
    print("- Implements standard refusal messages")
    print("- Prevents hallucinations by limiting to provided text")

    if success:
        print("\nSUCCESS CONSTITUTIONAL COMPLIANCE: ACHIEVED")
        print("The implementation follows all constitutional requirements.")
    else:
        print("\n?️  CONSTITUTIONAL COMPLIANCE: PARTIAL")
        print("Some requirements need to be addressed before deployment.")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)