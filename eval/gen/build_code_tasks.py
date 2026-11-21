"""Build eval/drafts/code_debug.json and code_gen.json and run the gold checks.

code_gen   : the reference solution must pass every hidden test.
code_debug : tests must PASS on the fixed code and FAIL on the buggy code (mutation check), and the
             buggy code is the fixed code with exactly one textual patch.
Run: .venv/Scripts/python.exe -m eval.gen.build_code_tasks
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from eval.gen import items_code_debug, items_code_gen
from eval.graders.code_tests import run_tests

OUT = Path(__file__).resolve().parents[1] / "drafts"


def split_tests(block: str) -> list:
    """Split a multi-line test block into runnable chunks (an assert, or a setup+assert group)."""
    lines = [ln for ln in block.strip().splitlines() if ln.strip()]
    # tests share a namespace per chunk; lines that are not asserts are setup for the assert that follows
    chunks = []
    for k, ln in enumerate(lines):
        if ln.lstrip().startswith("assert "):
            chunks.append(ln)
        else:  # first non-assert line starts a stateful group that runs the rest of the block in order
            chunks.append("\n".join(lines[k:]))
            break
    return chunks


DEBUG_PROMPTS = [
    ("neutral", "This function should {desc}, but it has a bug. Find and fix it:\n\n```python\n{code}```"),
    ("imperative", "Fix the bug in the following Python function.\nIntended behaviour: it should {desc}.\n\n```python\n{code}```"),
    ("casual", "my `{name}` function is giving wrong results and i can't see why. it's supposed to {desc}. here's the code:\n\n```python\n{code}```\nwhat's wrong with it?"),
    ("embedded", "I'm reviewing a teammate's pull request and a QA test is failing on this helper. The docstring says it should {desc}.\n\n```python\n{code}```\n\nCan you work out the problem and give me the corrected function?"),
]
GEN_PROMPTS = [
    ("neutral", "Write a Python function `{sig}` that {spec}."),
    ("imperative", "Implement `{sig}` in Python. It {spec2}."),
    ("casual", "need a python function `{sig}` - it {spec2}. can you write it?"),
    ("embedded", "I'm building a small utility module and I need one more helper. Please write the Python function `{sig}`; it {spec2}. Edge cases matter, so please handle them."),
]


def verb3(spec: str) -> str:
    """'returns ...' / 'counts ...' already third person; spec text is used as-is after 'it'."""
    return spec


def build_debug():
    rng = random.Random(11)
    items = []
    for name, desc, fixed, (find, rep), tests, diff, bug in items_code_debug.ITEMS:
        assert fixed.count(find) == 1, f"{name}: patch target must occur once"
        buggy = fixed.replace(find, rep)
        assert buggy != fixed
        chunks = split_tests(tests)
        ok_f, err_f, fatal_f = run_tests(fixed, chunks)
        assert all(ok_f), f"{name}: tests fail on FIXED code: {err_f} {fatal_f}"
        ok_b, err_b, fatal_b = run_tests(buggy, chunks)
        assert not all(ok_b), f"{name}: tests PASS on buggy code (weak tests)"
        n_caught = sum(1 for x in ok_b if not x)
        style, tpl = DEBUG_PROMPTS[len(items) % 4] if False else rng.choice(DEBUG_PROMPTS)
        prompt = tpl.format(desc=desc, code=buggy, name=name)
        items.append(dict(
            prompt=prompt, category="code_debug", grader="code_tests",
            gold={"entry_point": name, "tests": chunks, "reference": fixed},
            source="hand", difficulty=diff, phrasing=style, bug_type=bug,
            note=f"Planted bug: {bug}. Tests pass on the reference fix ({len(chunks)}/{len(chunks)}) and "
                 f"{n_caught}/{len(chunks)} fail on the buggy version.",
            gold_checks=f"mutation: reference passes {len(chunks)}/{len(chunks)}, buggy fails {n_caught}",
        ))
    return items


def build_gen():
    rng = random.Random(12)
    items = []
    for name, sig, spec, ref, tests, diff in items_code_gen.ITEMS:
        chunks = split_tests(tests)
        ok, err, fatal = run_tests(ref, chunks)
        assert all(ok), f"{name}: reference fails tests: {err} {fatal}"
        style, tpl = rng.choice(GEN_PROMPTS)
        prompt = tpl.format(sig=sig, spec=spec, spec2=spec)
        items.append(dict(
            prompt=prompt, category="code_gen", grader="code_tests",
            gold={"entry_point": name, "tests": chunks, "reference": ref},
            source="hand", difficulty=diff, phrasing=style,
            note=f"Reference solution passes all {len(chunks)} hidden tests (edge cases: empty/zero/ties as specified).",
            gold_checks=f"reference passes {len(chunks)}/{len(chunks)}",
        ))
    return items


def finish(items, prefix, seed):
    random.Random(seed).shuffle(items)
    for i, it in enumerate(items, 1):
        it["id"] = f"{prefix}-{i:03d}"
        it["split"] = "unsplit"
    return items


def main():
    OUT.mkdir(exist_ok=True)
    for name, items in (("code_debug", build_debug()), ("code_gen", build_gen())):
        assert len(items) == 50, (name, len(items))
        assert len({i["prompt"] for i in items}) == 50
        finish(items, name, 21)
        (OUT / f"{name}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
        print(name, Counter(i["difficulty"] for i in items), Counter(i["phrasing"] for i in items))


if __name__ == "__main__":
    main()
