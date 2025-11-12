import tempfile, pathlib, subprocess, textwrap, os
from langchain_core.tools import tool

IMAGE = "python:3.12-slim"

@tool("code_exec")
def code_exec(solution_code: str, test_code: str, timeout: int = 12) -> str:
    """
    Run solution.py + tests in a Docker container. Return stdout/stderr.
    """
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp)

        (p / "solution.py").write_text(solution_code, encoding="utf-8")
        runner = textwrap.dedent(f"""
import sys
sys.path.insert(0, ".")
import solution  # ensure syntax/import ok

G = {{"__name__": "__main__"}}
G.update(solution.__dict__)

try:
    exec(compile({test_code!r}, "tests", "exec"), G, G)
    print("OK")
except AssertionError as e:
    print("ASSERTION:", e); sys.exit(1)
except Exception as e:
    print("ERROR:", repr(e)); sys.exit(2)
""")
        (p / "run_tests.py").write_text(runner, encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONHASHSEED"] = "0" 

        cmd = [
            "docker","run","--rm",
            "--network=none","--cpus=1","--memory=512m","--pids-limit=128","--read-only",
            "-v", f"{p}:/work:ro","-w","/work",
            "--tmpfs","/tmp:rw,size=32m","--tmpfs","/var/tmp:rw,size=32m",
            IMAGE,"python","-I","run_tests.py",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired as e:
            return f"TIMEOUT ({timeout}s)\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        out = (proc.stdout or "") + (proc.stderr or "")
        return out
