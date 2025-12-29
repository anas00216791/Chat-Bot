"""
Mock RAG Chatbot Server for Testing

This server simulates the RAG chatbot API responses without requiring
a database or Claude API access. Useful for frontend development and testing.
"""
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import random

app = FastAPI(
    title="Mock Book RAG Chatbot API",
    description="Mock API for testing the frontend without database or Claude API",
    version="1.0.0"
)

# Sample book content for mock responses
SAMPLE_BOOK_CONTENT = [
    "ROS 2 (Robot Operating System 2) is a flexible framework for developing robot applications. It provides a collection of libraries and tools that help software developers create robot applications.",
    "A robot is a programmable machine that can carry out a series of actions automatically. Robotics combines engineering and computer science to design, construct, and operate robots.",
    "PID controllers are used in robotics for motion control. They calculate an error value as the difference between a desired setpoint and a measured process variable.",
    "Gazebo is a robotics simulator that provides accurate physics simulation and support for robot models. It's commonly used for testing and validating robot algorithms.",
    "Computer vision in robotics involves processing visual information to enable robots to navigate and interact with their environment.",
    "Navigation in robotics involves path planning, obstacle avoidance, and localization. The ROS navigation stack provides tools for these tasks.",
    "Machine learning in robotics enables robots to improve performance over time through experience. It's used for perception, control, and decision making.",
    "Sensor fusion combines data from multiple sensors to improve the accuracy and reliability of information obtained by a robot.",
]

class QueryRequest(BaseModel):
    query: str
    selected_text: Optional[str] = None
    mode: str = "book_scope"  # "book_scope" or "selected_text_only"
    max_tokens: int = 1500

class QueryResponse(BaseModel):
    success: bool
    answer: str
    sources: List[str]
    context_used: bool
    metadata: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    database_connected: bool

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        database_connected=True  # Always true for mock server
    )

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Main query endpoint that handles both book-scope and selected-text-only modes
    """
    # Simulate processing delay
    await asyncio.sleep(random.uniform(0.5, 1.5))

    # Check if mode is valid
    if request.mode not in ["book_scope", "selected_text_only"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'book_scope' or 'selected_text_only'")

    # Generate response based on mode
    if request.mode == "selected_text_only":
        if not request.selected_text:
            # No selected text provided, return refusal
            return QueryResponse(
                success=False,
                answer="I cannot answer this question without selected text. Please select text on the page and try again.",
                sources=[],
                context_used=False,
                metadata={
                    "was_refused": True,
                    "reason": "no_selected_text"
                }
            )
        else:
            # Process based on selected text
            answer = generate_answer_from_selected_text(request.query, request.selected_text)
            return QueryResponse(
                success=True,
                answer=answer,
                sources=["Selected Text"],
                context_used=True,
                metadata={
                    "was_refused": False,
                    "token_count": len(answer.split()),
                    "selected_text_used": True
                }
            )
    else:  # book_scope mode
        # Try to find relevant content based on the query
        answer, sources = generate_answer_from_book_scope(request.query)

        if "not available in the provided text" in answer:
            # Information not found in book content
            return QueryResponse(
                success=False,
                answer=answer,
                sources=[],
                context_used=False,
                metadata={
                    "was_refused": True,
                    "reason": "insufficient_context"
                }
            )
        else:
            return QueryResponse(
                success=True,
                answer=answer,
                sources=sources,
                context_used=True,
                metadata={
                    "was_refused": False,
                    "token_count": len(answer.split()),
                    "selected_text_used": False
                }
            )

def generate_answer_from_selected_text(query: str, selected_text: str) -> str:
    """Generate an answer based only on the selected text"""
    query_lower = query.lower()
    selected_lower = selected_text.lower()

    # Check if the selected text contains information relevant to the query
    if any(keyword in selected_lower for keyword in ['robot', 'ros', 'navigation', 'controller', 'gazebo', 'vision', 'sensor']):
        # Generate a response based on the selected text
        if 'what' in query_lower and 'robot' in selected_lower:
            return f"Based on the selected text, a robot is {selected_text.split('robot')[1].split('.')[0].strip()}."
        elif 'ros' in query_lower and 'ros' in selected_lower:
            return f"According to the selected text, ROS 2 {selected_text.split('ROS 2')[1].split('.')[0].strip()}."
        else:
            return f"Based on the selected text: {selected_text[:200]}{'...' if len(selected_text) > 200 else ''}"
    else:
        # If selected text doesn't contain relevant information
        return "This information is not available in the provided text."

def generate_answer_from_book_scope(query: str) -> tuple[str, List[str]]:
    """Generate an answer based on book content"""
    query_lower = query.lower()

    # Look for relevant content in the sample book content
    relevant_content = []
    sources = []

    for i, content in enumerate(SAMPLE_BOOK_CONTENT):
        if any(keyword in content.lower() for keyword in query_lower.split()):
            relevant_content.append(content)
            sources.append(f"Chapter {i+1}")

    if not relevant_content:
        # If no relevant content found, check if it's a general robotics question
        if any(keyword in query_lower for keyword in ['robot', 'robotics', 'ros', 'navigation', 'control', 'sensor', 'vision', 'gazebo', 'machine learning']):
            # Pick a relevant piece of content that might answer the question
            for content in SAMPLE_BOOK_CONTENT:
                if any(keyword in content.lower() for keyword in ['robot', 'robotics', 'ros', 'navigation', 'control', 'sensor', 'vision', 'gazebo', 'machine learning']):
                    relevant_content.append(content)
                    sources.append("General Chapter")
                    break

        if not relevant_content:
            return "This information is not available in the provided text.", []

    # Generate a response using the relevant content
    combined_content = " ".join(relevant_content[:2])  # Use first 2 relevant pieces
    if len(combined_content) > 300:
        combined_content = combined_content[:300] + "..."

    if 'what is' in query_lower or 'what does' in query_lower:
        return f"Based on the book content: {combined_content}", sources
    elif 'how' in query_lower:
        return f"According to the book: {combined_content}", sources
    elif 'explain' in query_lower:
        return f"The book explains: {combined_content}", sources
    else:
        return f"Based on the book content: {combined_content}", sources

if __name__ == "__main__":
    import uvicorn
    print("Starting Mock RAG Chatbot Server...")
    print("This server simulates the RAG API without requiring a database or Claude API")
    print("Available endpoints:")
    print("  - GET  /health")
    print("  - POST /query")
    print("\nTo test the frontend, make sure this server is running on http://localhost:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000)