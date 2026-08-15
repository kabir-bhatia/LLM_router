# Phase 3 -- Classification Accuracy Report

`eval/labeled_prompts.json`, 108 prompts, 5 flagged borderline.

## Headline numbers

| classifier | n | accuracy | macro-avg recall |
|---|---|---|---|
| Rule-based (all) | 108 | 50.9% | 41.0% |
| Rule-based (excl. borderline) | 103 | 51.5% | 42.7% |
| LLM-based (all) | 108 | 79.6% | 82.6% |
| LLM-based (excl. borderline) | 103 | 82.5% | 89.7% |

**Accuracy** is the naive score. **Macro-avg recall** averages per-class recall instead of pooling all prompts, so it isn't inflated by whichever tier happens to be the majority class in this dataset (SIMPLE, at 55%) -- treat macro-avg recall as the more honest number here.

LLM classification cost for this full eval run: **$0.007976** (108 successful calls).

## Confusion matrices (all prompts, including borderline)

### Rule-based

| true \ pred | simple | medium | complex |
|---|---|---|---|
| **simple** | 49 | 10 | 0 |
| **medium** | 9 | 6 | 0 |
| **complex** | 1 | 33 | 0 |

| tier | precision | recall | f1 | support |
|---|---|---|---|---|
| simple | 0.83 | 0.83 | 0.83 | 59 |
| medium | 0.12 | 0.40 | 0.19 | 15 |
| complex | 0.00 | 0.00 | 0.00 | 34 |

### LLM-based

| true \ pred | simple | medium | complex |
|---|---|---|---|
| **simple** | 40 | 18 | 1 |
| **medium** | 0 | 12 | 3 |
| **complex** | 0 | 0 | 34 |

| tier | precision | recall | f1 | support |
|---|---|---|---|---|
| simple | 1.00 | 0.68 | 0.81 | 59 |
| medium | 0.40 | 0.80 | 0.53 | 15 |
| complex | 0.89 | 1.00 | 0.94 | 34 |

## Accuracy by domain (rule-based)

| domain | n | accuracy |
|---|---|---|
| analysis | 24 | 50.0% |
| architecture | 24 | 37.5% |
| codegen | 24 | 50.0% |
| summarization | 12 | 58.3% |
| support | 24 | 62.5% |

## Accuracy by domain (LLM-based)

| domain | n | accuracy |
|---|---|---|
| analysis | 24 | 91.7% |
| architecture | 24 | 62.5% |
| codegen | 24 | 66.7% |
| summarization | 12 | 91.7% |
| support | 24 | 91.7% |

## Where the two classifiers disagree (66 prompts)

By definition rule_pred != llm_pred here, so exactly one of them can match true_tier, or neither can -- "both correct" isn't a possible outcome in this table.

| id | true | rule pred | llm pred | who was right |
|---|---|---|---|---|
| sup-007 | complex | medium | complex | llm |
| sup-010 | complex | medium | complex | llm |
| sup-012 | medium | simple | medium | llm |
| sup-013 | simple | simple | medium | rule |
| sup-014 | complex | medium | complex | llm |
| sup-017 | complex | medium | complex | llm |
| sup-018 | simple | medium | simple | llm |
| sup-019 | medium | simple | complex | neither |
| sup-022 | complex | medium | complex | llm |
| sup-024 | complex | medium | complex | llm |
| code-001 | simple | simple | medium | rule |
| code-003 | complex | medium | complex | llm |
| code-004 | simple | medium | complex | neither |
| code-005 | complex | medium | complex | llm |
| code-006 | simple | simple | medium | rule |
| code-007 | simple | simple | medium | rule |
| code-008 | medium | simple | medium | llm |
| code-009 | complex | medium | complex | llm |
| code-010 | simple | simple | medium | rule |
| code-011 | simple | medium | simple | llm |
| code-012 | complex | medium | complex | llm |
| code-014 | medium | simple | medium | llm |
| code-015 | complex | medium | complex | llm |
| code-016 | simple | simple | medium | rule |
| code-017 | simple | medium | simple | llm |
| code-018 | complex | medium | complex | llm |
| code-019 | simple | simple | medium | rule |
| code-020 | medium | medium | complex | rule |
| code-023 | complex | medium | complex | llm |
| arch-003 | complex | medium | complex | llm |
| arch-005 | complex | medium | complex | llm |
| arch-006 | simple | simple | medium | rule |
| arch-007 | complex | medium | complex | llm |
| arch-009 | simple | simple | medium | rule |
| arch-010 | complex | medium | complex | llm |
| arch-011 | medium | simple | medium | llm |
| arch-012 | complex | medium | complex | llm |
| arch-014 | simple | simple | medium | rule |
| arch-015 | complex | medium | complex | llm |
| arch-016 | simple | simple | medium | rule |
| arch-017 | complex | medium | complex | llm |
| arch-018 | simple | simple | medium | rule |
| arch-019 | medium | simple | medium | llm |
| arch-020 | complex | medium | complex | llm |
| arch-021 | simple | simple | medium | rule |
| arch-022 | simple | medium | simple | llm |
| arch-023 | complex | medium | complex | llm |
| summ-003 | complex | medium | complex | llm |
| summ-006 | simple | medium | simple | llm |
| summ-008 | complex | medium | complex | llm |
| summ-010 | medium | simple | complex | neither |
| summ-012 | complex | simple | complex | llm |
| anal-003 | complex | medium | complex | llm |
| anal-005 | complex | medium | complex | llm |
| anal-007 | complex | medium | complex | llm |
| anal-008 | simple | simple | medium | rule |
| anal-010 | complex | medium | complex | llm |
| anal-012 | medium | simple | medium | llm |
| anal-013 | complex | medium | complex | llm |
| anal-015 | simple | medium | simple | llm |
| anal-016 | complex | medium | complex | llm |
| anal-018 | medium | simple | medium | llm |
| anal-019 | complex | medium | complex | llm |
| anal-021 | complex | medium | complex | llm |
| anal-022 | simple | simple | medium | rule |
| anal-024 | complex | medium | complex | llm |

Of 66 disagreements: rule-correct=16, llm-correct=47, neither-correct=3.

## Misclassified prompts (rule-based)

- `sup-007` true=**complex** pred=**medium** -- A user is threatening to leave a 1-star public review unless we refund a purchase that's o
- `sup-010` true=**complex** pred=**medium** -- We're seeing a pattern where enterprise customers on the annual plan churn at 3x the rate 
- `sup-012` true=**medium** pred=**simple** -- Explain to a non-technical customer why their exported CSV file shows dates in the wrong f
- `sup-014` true=**complex** pred=**medium** -- A GDPR data deletion request came in for a user who also has an active dispute with our bi
- `sup-017` true=**complex** pred=**medium** -- Design an escalation policy for support tickets that accounts for customer tier (free/pro/
- `sup-018` true=**simple** pred=**medium** -- List the steps a customer needs to take to enable two-factor authentication.
- `sup-019` true=**medium** pred=**simple** -- Translate our privacy policy summary into French, Spanish, and German, and flag any terms 
- `sup-022` true=**complex** pred=**medium** -- Our support macros are inconsistent across three regional teams (US, EU, APAC), each havin
- `sup-024` true=**complex** pred=**medium** -- A customer's account was auto-suspended by our fraud detection system for unusual login pa
- `code-003` true=**complex** pred=**medium** -- Design a rate limiter that needs to work correctly across three regional datacenters with 
- `code-004` true=**simple** pred=**medium** -- I have this Python code and it's throwing a KeyError, can you fix it:
```python
config = {
- `code-005` true=**complex** pred=**medium** -- My distributed lock (built on Redis SETNX with a TTL) occasionally releases early under lo
- `code-008` true=**medium** pred=**simple** -- Explain what a race condition is, with a simple example.
- `code-009` true=**complex** pred=**medium** -- Design the database schema for a multi-tenant SaaS app where tenants can have custom field
- `code-011` true=**simple** pred=**medium** -- What's the time complexity of binary search?
- `code-012` true=**complex** pred=**medium** -- We need to migrate a 200M-row Postgres table to add a new NOT NULL column with a computed 
- `code-014` true=**medium** pred=**simple** -- Write a function to reverse a linked list.
- `code-015` true=**complex** pred=**medium** -- Our authentication service issues JWTs with a 24-hour expiry, but we just discovered that 
- `code-017` true=**simple** pred=**medium** -- Rename all instances of `userId` to `user_id` in this snippet:
```javascript
function getU
- `code-018` true=**complex** pred=**medium** -- Design an algorithm to detect cycles in a dependency graph of microservices, where the gra
- `code-023` true=**complex** pred=**medium** -- We're seeing intermittent 3-5 second latency spikes on a service that normally responds in
- `arch-003` true=**complex** pred=**medium** -- Design the system architecture for a real-time collaborative document editor (like Google 
- `arch-005` true=**complex** pred=**medium** -- We're migrating a 15-year-old monolith serving 40M requests/day to microservices, but the 
- `arch-007` true=**complex** pred=**medium** -- Design a threat model for a fintech API that handles wire transfers, considering insider t
- `arch-008` true=**simple** pred=**medium** -- Convert this list of services into a simple architecture diagram description: API gateway,
- `arch-010` true=**complex** pred=**medium** -- Design a notification system that needs to deliver push, email, and SMS notifications to 2
- `arch-011` true=**medium** pred=**simple** -- Why would you use a message queue instead of direct API calls between services?
- `arch-012` true=**complex** pred=**medium** -- Our API gateway needs to support both synchronous request/response for mobile clients and 
- `arch-013` true=**simple** pred=**medium** -- Define 'idempotency' in the context of API design.
- `arch-015` true=**complex** pred=**medium** -- Design a disaster recovery plan for a system with a 4-hour RTO and 15-minute RPO, spanning
- `arch-017` true=**complex** pred=**medium** -- We need to design multi-region active-active architecture for an inventory system where ov
- `arch-019` true=**medium** pred=**simple** -- Explain the producer-consumer pattern with a simple analogy.
- `arch-020` true=**complex** pred=**medium** -- Design the access control model for an internal admin tool where support agents need to vi
- `arch-022` true=**simple** pred=**medium** -- Format this list of architecture decision record titles into a numbered index: Use Postgre
- `arch-023` true=**complex** pred=**medium** -- Design a caching strategy for a product catalog page that needs fresh pricing (updated wit
- `arch-024` true=**simple** pred=**medium** -- What's the difference between authentication and authorization?
- `summ-003` true=**complex** pred=**medium** -- Read this 40-page vendor security audit and produce an executive summary that (a) ranks th
- `summ-006` true=**simple** pred=**medium** -- Condense this meeting transcript into action items only, one line each: [30 minutes of bac
- `summ-008` true=**complex** pred=**medium** -- Synthesize three conflicting internal reports on why a product launch underperformed -- on
- `summ-010` true=**medium** pred=**simple** -- Turn this wall of release notes spanning 8 versions into a single 'what's new since your l
- `summ-012` true=**complex** pred=**simple** -- Summarize the key differences between two competing vendor proposals (each 20 pages) for a
- `anal-003` true=**complex** pred=**medium** -- We have two years of A/B test data showing a new checkout flow increases conversion by 4% 
- `anal-005` true=**complex** pred=**medium** -- Three separate teams each independently concluded, from the same underlying support ticket
- `anal-007` true=**complex** pred=**medium** -- Evaluate whether we should build our own feature-flagging system in-house versus buying a 
- `anal-010` true=**complex** pred=**medium** -- We're deciding between two hiring strategies for scaling a support team: hiring 10 general
- `anal-012` true=**medium** pred=**simple** -- Explain why a company might choose to go public via direct listing instead of a traditiona
- `anal-013` true=**complex** pred=**medium** -- A pricing experiment shows that raising prices 10% increased revenue per user but total re
- `anal-015` true=**simple** pred=**medium** -- Categorize these five customer complaints as 'billing', 'technical', or 'product feedback'
- `anal-016` true=**complex** pred=**medium** -- We need to decide whether to sunset a legacy product used by 200 loyal customers generatin
- `anal-018` true=**medium** pred=**simple** -- Explain the difference between leading and lagging indicators, with one business example o
- `anal-019` true=**complex** pred=**medium** -- Two internal surveys measuring employee satisfaction, run one month apart using different 
- `anal-021` true=**complex** pred=**medium** -- Compare the total cost of ownership of running our own Kubernetes cluster versus using a m
- `anal-024` true=**complex** pred=**medium** -- A stakeholder is citing a statistic that '73% of users prefer the new design' from a surve

## Misclassified prompts (LLM-based)

- `sup-013` true=**simple** pred=**medium** -- What is the difference between a refund and store credit in our system?
- `sup-019` true=**medium** pred=**complex** -- Translate our privacy policy summary into French, Spanish, and German, and flag any terms 
- `code-001` true=**simple** pred=**medium** -- Write a Python function that checks if a string is a palindrome.
- `code-004` true=**simple** pred=**complex** -- I have this Python code and it's throwing a KeyError, can you fix it:
```python
config = {
- `code-006` true=**simple** pred=**medium** -- What does the `git rebase -i` command do?
- `code-007` true=**simple** pred=**medium** -- Write a SQL query that returns the top 5 customers by total order value from an `orders` t
- `code-010` true=**simple** pred=**medium** -- Convert this function from synchronous to async in Python:
```python
def fetch_user(user_i
- `code-016` true=**simple** pred=**medium** -- What's the difference between `let`, `const`, and `var` in JavaScript?
- `code-019` true=**simple** pred=**medium** -- Write a regex that matches valid US phone numbers in the format (XXX) XXX-XXXX.
- `code-020` true=**medium** pred=**complex** -- Compare REST and GraphQL for a public API that will be consumed by both a mobile app with 
- `arch-006` true=**simple** pred=**medium** -- What's the difference between vertical and horizontal scaling?
- `arch-008` true=**simple** pred=**medium** -- Convert this list of services into a simple architecture diagram description: API gateway,
- `arch-009` true=**simple** pred=**medium** -- What is the CAP theorem?
- `arch-013` true=**simple** pred=**medium** -- Define 'idempotency' in the context of API design.
- `arch-014` true=**simple** pred=**medium** -- What is database sharding?
- `arch-016` true=**simple** pred=**medium** -- List three pros and three cons of using Kubernetes.
- `arch-018` true=**simple** pred=**medium** -- What's a reverse proxy used for?
- `arch-021` true=**simple** pred=**medium** -- What does 'eventual consistency' mean?
- `arch-024` true=**simple** pred=**medium** -- What's the difference between authentication and authorization?
- `summ-010` true=**medium** pred=**complex** -- Turn this wall of release notes spanning 8 versions into a single 'what's new since your l
- `anal-008` true=**simple** pred=**medium** -- List three advantages of a subscription pricing model over one-time purchases.
- `anal-022` true=**simple** pred=**medium** -- Is this a valid syllogism: all engineers like coffee, Sam likes coffee, therefore Sam is a
