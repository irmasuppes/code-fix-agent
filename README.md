## LLM-Based Python Bug Fixing Agent

This project implements a ReAct-style agent that repairs buggy Python functions using a lightweight open-source LLM (served via Ollama) and evaluates fixes on the subset of HumanEvalFix (Python) benchmark inside a Docker sandbox.

Setup
-----
Make sure you have:
- Ollama running locally
- Docker daemon active 
```
uv sync
ollama pull qwen3:0.6b
```

Run
--------
Run the agent on a sample of 10 tasks:
```
uv run main.py --model qwen3:0.6b --data humanevalfix_python.jsonl --limit 10
```
To evaluate the full dataset or allow more iterative repair steps:
```
uv run main.py --model qwen3:0.6b --data humanevalfix_python.jsonl --max-steps 10
```

All results are saved to agent_results.json

Evaluation (pass@1)
--------
Evaluation was conducted on 10 Python tasks from the [HumanEvalPack dataset](https://huggingface.co/datasets/bigcode/humanevalpack).

|   Metric   |    Score   |
| :--------: | :--------: |
| **pass@1** | **3 / 10** |
