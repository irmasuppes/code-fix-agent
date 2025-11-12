"""
LLM-Based Python Bug Fixing Agent

This project implements a ReAct-style agent that repairs buggy Python functions using a lightweight open-source LLM (served via Ollama) and evaluates fixes on the subset of HumanEvalFix (Python) benchmark inside a Docker sandbox.

Key points
----------


Setup
-----
uv sync

Make sure you have:
- Ollama running locally
- Docker daemon active 

# download local model
ollama pull qwen3:0.6b

Run
--------

uv run main.py --model qwen3:0.6b --data humanevalfix_python.jsonl --limit 10
"""