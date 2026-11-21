"""Dev-set-A development check for the math solver (what the solver was built against)."""
from router.data import load_dev
from router.solvers.math_solver import solve_math

d = [t for t in load_dev() if t["category"] == "math" and t["template_set"] == "A"]
ok = ans = 0
for t in d:
    r = solve_math(t["prompt"])
    g = str(t["gold"]["answer"])
    ans += r.answered
    ok += r.answered and r.answer == g
    print(t["id"], r.answer, g, r.recipe or r.reason, "" if (not r.answered or r.answer == g) else "  <<< WRONG")
print(ans, ok, len(d))
