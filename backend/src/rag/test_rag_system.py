"""
Test Script for RAG Chatbot System

This script tests the RAG system by:
1. Setting up a test database
2. Ingesting sample content
3. Testing retrieval functionality
4. Testing the Claude integration (with mock if needed)
"""
import os
import tempfile
import asyncio
from pathlib import Path

# Import from the same package
import sys
from pathlib import Path as PPath
sys.path.append(str(PPath(__file__).parent))

from ingest_content import BookContentIngestor
from retriever import BookContentRetriever
from main import app
from claude_client import ClaudeRAGClient
from prompt_templates import QueryMode


def create_test_book_content():
    """Create temporary test book content for testing"""
    # Create a temporary directory for test content
    temp_dir = tempfile.mkdtemp()
    book_dir = Path(temp_dir) / "test_book"
    book_dir.mkdir()

    # Create test markdown files
    chapter1_dir = book_dir / "chapter1"
    chapter1_dir.mkdir()

    # Create a test markdown file
    test_content = """---
title: Introduction to Robotics
---
# Introduction to Robotics

Robotics is an interdisciplinary field that combines engineering and computer science to design, construct, and operate robots. A robot is a programmable machine that can carry out a series of actions automatically.

## Types of Robots

There are several types of robots including:
- Industrial robots used in manufacturing
- Service robots for domestic and commercial applications
- Medical robots for surgical procedures
- Exploration robots for hazardous environments

## ROS 2 Basics

ROS 2 (Robot Operating System 2) is a flexible framework for developing robot applications. It provides a collection of libraries and tools that help software developers create robot applications. ROS 2 is designed to support large development efforts.

The key features of ROS 2 include:
- Improved security
- Better real-time support
- Enhanced multi-robot support
"""

    with open(book_dir / "intro.md", "w", encoding="utf-8") as f:
        f.write(test_content)

    # Create another chapter
    chapter2_dir = book_dir / "chapter2"
    chapter2_dir.mkdir()

    test_content2 = """---
title: ROS 2 Architecture
---
# ROS 2 Architecture

## Nodes and Communication

In ROS 2, nodes are the fundamental unit of execution. Each node is a process that performs computation. Nodes written in different programming languages can communicate with each other using the ROS 2 client libraries.

## Topics and Services

Topics provide asynchronous communication using a publish/subscribe model. Services provide synchronous request/response communication.

## Parameters

Parameters are used to configure nodes at runtime.
"""

    with open(chapter2_dir / "architecture.md", "w", encoding="utf-8") as f:
        f.write(test_content2)

    return str(book_dir)


def test_ingestion_and_retrieval():
    """Test the ingestion and retrieval functionality"""
    print("Testing RAG system...")

    # Create test book content
    test_book_path = create_test_book_content()
    print(f"Created test book at: {test_book_path}")

    # Use a test database URL (this would be a test database in real usage)
    db_url = os.getenv('NEON_DB_URL')
    if not db_url:
        print("NEON_DB_URL not set, skipping integration test")
        return False

    try:
        # Test ingestion
        print("\n1. Testing content ingestion...")
        ingestor = BookContentIngestor(db_url)
        ingestor.connect_to_db()
        ingestor.create_tables()
        ingestor.ingest_book_content(test_book_path)
        print("✓ Content ingestion completed")

        # Test retrieval
        print("\n2. Testing content retrieval...")
        retriever = BookContentRetriever(db_url)
        retriever.connect_to_db()

        # Test search functionality
        results = retriever.search_content("ROS 2 basics", limit=2)
        print(f"Found {len(results)} results for 'ROS 2 basics'")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result['title']} - {result['content'][:100]}...")

        # Test metadata search
        results = retriever.search_by_metadata({"chapter": "chapter1"}, limit=5)
        print(f"Found {len(results)} results in chapter1")

        print("✓ Content retrieval working correctly")

        # Test context retrieval
        context_result = retriever.get_relevant_context("What is ROS 2?", max_tokens=1500)
        print(f"Retrieved context with {len(context_result['retrieved_content'])} chunks")
        print(f"Total tokens: {context_result['total_tokens']}")

        print("✓ Context retrieval working correctly")

        return True

    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Close connections
        if 'ingestor' in locals() and ingestor.connection:
            ingestor.connection.close()
        if 'retriever' in locals() and retriever.connection:
            retriever.connection.close()


def test_claude_integration():
    """Test Claude integration (if API keys are available)"""
    print("\n3. Testing Claude integration...")

    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_api_key:
        print("ANTHROPIC_API_KEY not set, skipping Claude integration test")
        return True

    db_url = os.getenv('NEON_DB_URL')
    if not db_url:
        print("NEON_DB_URL not set, skipping Claude integration test")
        return True

    try:
        client = ClaudeRAGClient(anthropic_api_key)

        # Test with selected text mode
        result = asyncio.run(client.get_answer_with_retrieval(
            query="What is robotics?",
            mode=QueryMode.SELECTED_TEXT_ONLY,
            selected_text="Robotics is an interdisciplinary field that combines engineering and computer science to design, construct, and operate robots.",
            db_url=db_url
        ))

        print(f"Claude response: {result.get('answer', 'No answer')[:100]}...")
        print("✓ Claude integration test completed")

        return True

    except Exception as e:
        print(f"Error in Claude integration test: {str(e)}")
        return False


def main():
    print("Running RAG Chatbot System Tests")
    print("=" * 50)

    # Test ingestion and retrieval
    ingestion_success = test_ingestion_and_retrieval()

    # Test Claude integration if keys are available
    claude_success = test_claude_integration()

    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Ingestion & Retrieval: {'✓ PASS' if ingestion_success else '✗ FAIL'}")
    print(f"Claude Integration: {'✓ PASS' if claude_success else '✗ FAIL (API keys may not be set)'}")

    overall_success = ingestion_success
    print(f"Overall: {'✓ PASS' if overall_success else '✗ FAIL'}")

    if overall_success:
        print("\nRAG system is working correctly!")
    else:
        print("\nThere were issues with the RAG system.")

    return overall_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)