"""Code grader: extract the function from the answer and run hidden tests in a subprocess.

Sandbox (best effort, enough for benchmark outputs): fresh interpreter in isolated mode, empty temp
cwd, scrubbed environment, sockets disabled, hard wall-clock timeout (default 5 s).
Gold: {"entry_point": "second_largest", "tests": ["assert second_largest([1,2]) == 1", ...]}
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

from .common import GradeResult, strip_thinking

TIMEOUT_S = 5.0

_HARNESS = r'''
import json, socket
def _blocked(*a, **k):
    raise OSError("network disabled in sandbox")
socket.socket = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
_results = []
_ns = {"__name__": "__sandbox__"}
try:
    exec(compile(open("solution.py", encoding="utf-8").read(), "solution.py", "exec"), _ns)
    _load_err = None
except BaseException as e:
    _load_err = type(e).__name__ + ": " + str(e)[:120]
tests = json.load(open("tests.json", encoding="utf-8"))
for t in tests:
    if _load_err:
        _results.append([False, _load_err])
        continue
    try:
        exec(compile(t, "test", "exec"), dict(_ns))
        _results.append([True, ""])
    except BaseException as e:
        _results.append([False, type(e).__name__ + ": " + str(e)[:120]])
print("@@RESULTS@@" + json.dumps(_results))
'''


def extract_code(response: str, entry_point=None):
    """Last fenced block defining entry_point (or the last block); fallback: raw text from first def."""
    text = strip_thinking(response)
    blocks = re.findall(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.DOTALL)
    if not blocks:
        m = re.search(r"```[a-zA-Z0-9_+-]*\n(.*)$", text, re.DOTALL)  # unterminated (truncated)
        if m:
            blocks = [m.group(1)]
    if blocks:
        if entry_point:
            with_def = [b for b in blocks if re.search(rf"def\s+{re.escape(entry_point)}\s*\(", b)]
            if with_def:
                return with_def[-1]
        return blocks[-1]
    i = text.find("def ")
    return text[i:] if i >= 0 else None


def run_tests(code: str, tests: list, timeout: float = TIMEOUT_S):
    """Run each test string against code. Returns (passes, errors, fatal)."""
    with tempfile.TemporaryDirectory() as d:
        for name, content in (("solution.py", code), ("tests.json", json.dumps(tests)),
                              ("harness.py", _HARNESS)):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(content)
        env = {k: v for k, v in os.environ.items() if k in ("SYSTEMROOT", "PATH", "TEMP", "TMP")}
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            p = subprocess.run([sys.executable, "-I", "harness.py"], cwd=d, env=env,
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return [False] * len(tests), ["timeout"] * len(tests), "timeout"
        m = re.search(r"@@RESULTS@@(.*)", p.stdout)
        if not m:
            return [False] * len(tests), ["crash"] * len(tests), (p.stderr or "no output")[-300:]
        res = json.loads(m.group(1))
        return [r[0] for r in res], [r[1] for r in res], None


def grade_code(response: str, gold: dict) -> GradeResult:
    code = extract_code(response, gold.get("entry_point"))
    if not code:
        return GradeResult(False, 0.0, "no code found", None)
    tests = gold["tests"]
    passes, errs, fatal = run_tests(code, tests, gold.get("timeout", TIMEOUT_S))
    n = sum(passes)
    ok = n == len(tests)
    detail = f"{n}/{len(tests)} tests passed" + (f" ({fatal})" if fatal else "")
    first_err = next((e for e in errs if e), "")
    return GradeResult(ok, n / len(tests), detail + (f"; first error: {first_err}" if first_err else ""),
                       code, meta={"passes": passes, "fatal": fatal})
