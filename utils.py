import re, textwrap

_THINK_BLOCK = re.compile(r'<think>.*?</think>', re.DOTALL | re.IGNORECASE)

_TOP_RE = re.compile(r'^\s*(def|class|import|from)\b')

_PYBODY = re.compile(r"<<<\s*PYBODY\s*>>>[\t ]*\n(.*?)\n[\t ]*<<<\s*END\s*>>>", re.DOTALL | re.IGNORECASE)
_PYMOD  = re.compile(r"<<<\s*PY\s*>>>[\t ]*\n(.*?)\n[\t ]*<<<\s*END\s*>>>", re.DOTALL | re.IGNORECASE)
_FENCE  = re.compile(r"```(?:python)?\n(.*?)\n```", re.DOTALL | re.IGNORECASE)

def strip_meta(s: str) -> str:
    # remove <think> ... </think> 
    s = _THINK_BLOCK.sub('', s or '')
    return s.strip()

def extract_body_block(s: str) -> str:
    m = re.search(r'<<<PYBODY>>>\n(.*?)\n<<<END>>>', s or '', re.DOTALL)
    if m: return m.group(1)
    m = re.search(r'```python\n(.*?)\n```', s or '', re.DOTALL)
    return m.group(1) if m else (s or '')


def wrap_with_signature(body: str, *, imports=None, signature=None, entry_point=None) -> str:
    body_clean = textwrap.dedent(body or "").strip("\n")

    if _TOP_RE.match(body_clean):
        imps = textwrap.dedent(imports or "").strip()
        needs_typing = any(t in body_clean for t in ("List","Tuple","Dict","Set","Optional"))
        if needs_typing and "from typing import" not in imps:
            imps = (imps + "\nfrom typing import *").strip() if imps else "from typing import *"
        head = "from __future__ import annotations\n"
        return "\n".join([head, imps, body_clean]).strip() if imps else (head + body_clean)

    if not signature and entry_point:
        signature = f"{entry_point}(*args, **kwargs):"
    def_line = (signature or "main_func(*args, **kwargs):").strip()
    if not def_line.startswith("def "):
        def_line = "def " + def_line
    if not def_line.endswith(":"):
        def_line += ":"

    lines = body_clean.splitlines()
    indented = "\n".join(("    " + ln) if ln.strip() else "    " for ln in lines) + "\n"

    imps = textwrap.dedent(imports or "").strip()
    needs_typing = any(t in (imps + def_line + body_clean) for t in ("List","Tuple","Dict","Set","Optional"))
    if needs_typing and "from typing import" not in imps:
        imps = (imps + "\nfrom typing import *").strip() if imps else "from typing import *"

    parts = ["from __future__ import annotations"]
    if imps:
        parts.append(imps)
    parts.append(def_line)
    parts.append(indented)
    return "\n".join(parts)


def _truncate(s: str, n: int = 1200) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "...[truncated]"


def extract_candidate(text: str) -> tuple[str, bool]:
    s = text or ""
    m = _PYBODY.search(s)
    if m:
        code = textwrap.dedent(m.group(1)).strip("\n")
        is_full = bool(_TOP_RE.match(code))
        return code, is_full
    m = _PYMOD.search(s)
    if m:
        return textwrap.dedent(m.group(1)).strip("\n"), True
    m = _FENCE.search(s)
    if m:
        code = textwrap.dedent(m.group(1)).strip("\n")
        return code, bool(_TOP_RE.match(code))
    code = textwrap.dedent(s).strip("\n")
    return code, bool(_TOP_RE.match(code))