"""Dev-set-A development check for the logic solver."""
from router.data import load_dev
from router.solvers.logic_solver import solve_logic

d = [t for t in load_dev() if t["category"] == "logic" and t["template_set"] == "A"]
ok = ans = 0
for t in d:
    r = solve_logic(t["prompt"])
    g = t["gold"]["answer"]
    ans += r.answered
    ok += r.answered and r.answer == g
    print(t["id"], r.answer, g, r.reason, "" if (not r.answered or r.answer == g) else "  <<< WRONG")
print(ans, ok, len(d))
