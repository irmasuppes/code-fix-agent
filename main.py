import argparse
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from docker_tool import code_exec
from utils import wrap_with_signature, strip_meta, _truncate, extract_candidate

@dataclass
class TaskItem:
    task_id: str
    prompt: str
    buggy_solution: str
    test: str
    imports: Optional[str] = None         
    signature: Optional[str] = None       
    entry_point: Optional[str] = None     

def load_jsonl(path: Path, limit: Optional[int] = None) -> List[TaskItem]:
    out: List[TaskItem] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            if not line.strip():
                continue
            r = json.loads(line)
            out.append(
                TaskItem(
                    task_id=str(r["task_id"]),
                    prompt=r.get("prompt", "") or "",
                    buggy_solution=r["buggy_solution"],
                    test=r["test"],
                    imports=r.get("import") or None,
                    signature=r.get("signature") or None,
                    entry_point=r.get("entry_point") or None,
                )
            )
    return out

SYSTEM_RULES = """You fix Python bugs.

STRICT OUTPUT:
Return only the function BODY between <<<PYBODY>>> and <<<END>>>.
No signature, no imports, no comments outside the body, no explanations.

Example:
<<<PYBODY>>>
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
<<<END>>>
"""


def build_agent(llm):
    return create_agent(llm, tools=[code_exec])

def evaluate(
    agent,
    tasks: List[TaskItem],
    max_steps: int = 5,
    debug: bool = False,
    show_code: bool = False
) -> Dict[str, Dict]:
    results: Dict[str, Dict] = {}

    for t in tasks:
        print(f"\n=== {t.task_id} ===")

        solution0 = wrap_with_signature(
            t.buggy_solution,
            imports=t.imports,
            signature=t.signature,
            entry_point=t.entry_point,
        )
        first_log = code_exec.invoke({"solution_code": solution0, "test_code": t.test})
        if debug:
            print("[baseline log]" + _truncate(first_log))

        last_log = first_log
        success = False

        # ReAct loop
        for step in range(1, max_steps + 1):
            user = f"""Attempt: {step}
TASK PROMPT:
{t.prompt}

BUGGY solution.py (wrapped):
{solution0}

LAST LOG:
{last_log}

Return only the function BODY wrapped in <<<PYBODY>>> and <<<END>>>."""
            resp = agent.invoke({"messages": [("system", SYSTEM_RULES), ("human", user)]})
            final_text = resp["messages"][-1].content if resp.get("messages") else ""

            clean_text = strip_meta(final_text)
            code_raw, is_full = extract_candidate(clean_text)

            if show_code:
                print("[candidate body]\n" + _truncate(code_raw, 1200))

            if not code_raw.strip():
                if debug:
                    print("[warn] model returned empty/ non-code body; skipping this step")
                last_log = "Empty body"
                continue

            solution = wrap_with_signature(
                code_raw,
                imports=t.imports,
                signature=t.signature,
                entry_point=t.entry_point,
            )
            log = code_exec.invoke({"solution_code": solution, "test_code": t.test})
            ok = ("OK" in log) and ("ASSERTION:" not in log) and ("ERROR:" not in log)
            print(f"step {step}: {'PASS' if ok else 'fail'}")
            if debug and not ok:
                print("[step log]" + _truncate(log))

            if ok:
                success = True
                results[t.task_id] = {"pass": True, "steps": step, "body": code_raw}
                break
            last_log = log

        if not success:
            results[t.task_id] = {"pass": False, "steps": max_steps, "last_log": last_log}

    return results

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:0.6b")   
    ap.add_argument("--data", type=Path, default=Path("humanevalfix_python.jsonl"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-steps", type=int, default=3)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--show-code", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()

    tasks = load_jsonl(args.data, limit=args.limit)

    llm = ChatOllama(model=args.model, temperature=0.2)
    agent = build_agent(llm)

    results = evaluate(agent, tasks, args.max_steps, args.debug, args.show_code)

    n = len(results)
    p1 = sum(1 for r in results.values() if r.get("pass") and r.get("steps") == 1)
    summary = {"num_tasks": n, "pass_at_1": p1, "pass_at_1_pct": round(100 * p1 / max(n, 1), 2)}
    print("\nSummary:", json.dumps(summary, indent=2))

    out = Path("agent_results.json")
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved results to {out.resolve()}")

if __name__ == "__main__":
    main()
