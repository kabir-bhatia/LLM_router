# Phase 4 -- Cost/Accuracy Tradeoff Report

Ran all 108 labeled prompts through the real production pipeline (`LLMRouter.classify` -> `ProviderManager.generate`), plus a real separate baseline generation on `gemini-2.5-pro` for every prompt (not a token-count re-pricing of the routed response -- see script docstring).

## Aggregate cost

| | total |
|---|---|
| Actual cost (routed) | $0.161112 |
| Baseline cost (always `gemini-2.5-pro`) | $0.310293 |
| Savings | $0.149181 (48.1%) |
| n (excluding failures) | 108 / 108 |

## Cost by true difficulty tier

| true tier | n | actual cost | baseline cost | savings % |
|---|---|---|---|---|
| simple | 59 | $0.059888 | $0.182086 | 67.1% |
| medium | 15 | $0.039342 | $0.069105 | 43.1% |
| complex | 34 | $0.061881 | $0.059101 | -4.7% |

**On the COMPLEX row possibly reading near-zero or negative:** that's expected, not a bug. A correctly-routed COMPLEX prompt's "actual" model already IS `gemini-2.5-pro` -- the same model as the baseline -- so actual and baseline cost for that row come from two *independent* generations of the identical model on the identical prompt (temperature 0.7), differing only by natural response-length variance between samples. A small swing either side of 0% here is sampling noise, not a routing failure; it would only be concerning if it were large and consistently negative.

## Misroutes

- **Under-routed** (sent cheaper than true difficulty warranted): 0 / 108 (0.0%)
- **Over-routed** (sent pricier than necessary -- money left on the table, not a quality risk): 21 / 108 (19.4%)
- **Matched** true difficulty exactly: 87 / 108 (80.6%)

Under-routing is the case that actually matters: a COMPLEX prompt answered by a SIMPLE-tier model is the cheapest possible wrong answer, and a wrong answer that reads as confident is worse than an expensive right one. Every under-routed prompt below is worth reading, not just counting.

### Over-routed prompts (21) -- wasted spend, not a quality risk

- `sup-019` (true **medium**, routed **complex**): Translate our privacy policy summary into French, Spanish, and German, and flag any terms (like 'dat
- `code-001` (true **simple**, routed **medium**): Write a Python function that checks if a string is a palindrome.
- `code-004` (true **simple**, routed **complex**): I have this Python code and it's throwing a KeyError, can you fix it:
```python
config = {"host": "l
- `code-006` (true **simple**, routed **medium**): What does the `git rebase -i` command do?
- `code-007` (true **simple**, routed **medium**): Write a SQL query that returns the top 5 customers by total order value from an `orders` table with 
- `code-010` (true **simple**, routed **medium**): Convert this function from synchronous to async in Python:
```python
def fetch_user(user_id):
    re
- `code-016` (true **simple**, routed **medium**): What's the difference between `let`, `const`, and `var` in JavaScript?
- `code-019` (true **simple**, routed **medium**): Write a regex that matches valid US phone numbers in the format (XXX) XXX-XXXX.
- `code-020` (true **medium**, routed **complex**): Compare REST and GraphQL for a public API that will be consumed by both a mobile app with strict ban
- `arch-006` (true **simple**, routed **medium**): What's the difference between vertical and horizontal scaling?
- `arch-008` (true **simple**, routed **medium**): Convert this list of services into a simple architecture diagram description: API gateway, auth serv
- `arch-009` (true **simple**, routed **medium**): What is the CAP theorem?
- `arch-013` (true **simple**, routed **medium**): Define 'idempotency' in the context of API design.
- `arch-014` (true **simple**, routed **medium**): What is database sharding?
- `arch-016` (true **simple**, routed **medium**): List three pros and three cons of using Kubernetes.
- `arch-018` (true **simple**, routed **medium**): What's a reverse proxy used for?
- `arch-021` (true **simple**, routed **medium**): What does 'eventual consistency' mean?
- `arch-024` (true **simple**, routed **medium**): What's the difference between authentication and authorization?
- `summ-010` (true **medium**, routed **complex**): Turn this wall of release notes spanning 8 versions into a single 'what's new since your last login'
- `anal-008` (true **simple**, routed **medium**): List three advantages of a subscription pricing model over one-time purchases.
- `anal-022` (true **simple**, routed **medium**): Is this a valid syllogism: all engineers like coffee, Sam likes coffee, therefore Sam is an engineer
