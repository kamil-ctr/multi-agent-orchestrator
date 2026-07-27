"""A small, fixed suite of prompts spanning every query type, used by
`python main.py benchmark` to compare agent performance under identical
conditions."""
from __future__ import annotations

BENCHMARK_PROMPTS: list[dict[str, str]] = [
    {"query_type": "factual", "prompt": "What is the capital of Australia?"},
    {"query_type": "factual", "prompt": "Who wrote the novel Pride and Prejudice?"},
    {"query_type": "creative", "prompt": "Write a four-line poem about autumn leaves."},
    {"query_type": "analytical", "prompt": "Compare the pros and cons of remote work versus office work."},
    {"query_type": "coding", "prompt": "Write a Python function that checks if a string is a palindrome."},
    {"query_type": "conversational", "prompt": "Hi! How are you doing today?"},
]
