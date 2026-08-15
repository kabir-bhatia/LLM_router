"""One-off script: apply hand-designed labels to eval/candidate_prompts.json.

Not part of the reusable pipeline -- run once to produce labeled_prompts.json,
then this file can be deleted or kept as a record of how the labels were set.
"""

import json
from collections import Counter
from pathlib import Path

LABELS = {
    # support
    "sup-001": ("simple", False, ""),
    "sup-002": ("medium", False, "multi-part customer request, but single-pass drafting acknowledging each ask -- not multi-step reasoning"),
    "sup-003": ("simple", False, ""),
    "sup-004": ("simple", False, ""),
    "sup-005": ("simple", False, ""),
    "sup-006": ("simple", False, ""),
    "sup-007": ("complex", False, "weighs brand risk against policy precedent and requires an escalation-process judgment call; a wrong call has real cost (public review, policy erosion)"),
    "sup-008": ("simple", False, ""),
    "sup-009": ("simple", False, ""),
    "sup-010": ("complex", False, "multi-hypothesis root-cause investigation requiring cross-team data, ordered by likelihood"),
    "sup-011": ("simple", False, ""),
    "sup-012": ("medium", False, "requires real domain knowledge (timezone/date serialization) explained for a non-technical audience, single pass"),
    "sup-013": ("simple", False, ""),
    "sup-014": ("complex", False, "GDPR deletion intersecting with an active billing dispute and a shared business account -- interacting legal constraints, high cost of a wrong call"),
    "sup-015": ("simple", False, ""),
    "sup-016": ("simple", False, ""),
    "sup-017": ("complex", False, "escalation policy must satisfy coverage, tier, and time-of-day simultaneously without burning out on-call -- interacting constraints"),
    "sup-018": ("simple", False, ""),
    "sup-019": ("medium", True, "translation itself is mechanical, but flagging cross-jurisdiction legal ambiguity per language requires real judgment -- not a pure SIMPLE transformation despite being a translation task"),
    "sup-020": ("simple", False, ""),
    "sup-021": ("simple", False, ""),
    "sup-022": ("complex", False, "unifying policy drift across three regional teams is an organizational change-management problem, not just an editing task"),
    "sup-023": ("simple", False, ""),
    "sup-024": ("complex", False, "conflicting signals (plausible travel story vs. active fraud investigation) with real business/legal risk on either resolution"),
    # codegen
    "code-001": ("simple", False, ""),
    "code-002": ("simple", False, ""),
    "code-003": ("complex", False, "multi-region active-active rate limiter under an outage-tolerance and strict latency budget -- classic distributed-systems tradeoff design"),
    "code-004": ("simple", False, "single-line fix for a narrow, local KeyError"),
    "code-005": ("complex", False, "intermittent concurrency bug with no local root cause and no staging repro -- the short prompt hides real difficulty"),
    "code-006": ("simple", False, ""),
    "code-007": ("simple", False, ""),
    "code-008": ("medium", False, "requires genuine understanding of concurrency, single self-contained explanation"),
    "code-009": ("complex", False, "custom fields, data-residency compliance, and scale must all be satisfied by the same schema -- interacting constraints"),
    "code-010": ("simple", False, "mechanical sync-to-async transformation of one function"),
    "code-011": ("simple", False, ""),
    "code-012": ("complex", False, "zero-downtime schema migration at scale under a strict write-latency budget -- real operational risk if done wrong"),
    "code-013": ("simple", False, ""),
    "code-014": ("medium", True, "matches the rubric's own MEDIUM example ('self-contained function for a clear spec'), though the solution is common enough that a case for SIMPLE exists"),
    "code-015": ("complex", False, "security incident remediation with an incomplete audit trail and an explicit tradeoff (blast-radius vs. forcing mass re-auth)"),
    "code-016": ("simple", False, ""),
    "code-017": ("simple", False, ""),
    "code-018": ("complex", False, "incremental cycle detection at scale that must stay correct under concurrent graph updates -- nontrivial algorithm design"),
    "code-019": ("simple", True, "well-defined single pattern, but borderline with MEDIUM under 'script for a clear spec'"),
    "code-020": ("medium", True, "a bounded comparison-then-recommend task; concrete constraints for two consumer profiles push toward COMPLEX but it's not multi-step system design"),
    "code-021": ("simple", False, ""),
    "code-022": ("medium", False, "self-contained script with a clear spec, moderate but single-threaded"),
    "code-023": ("complex", False, "no correlated metric signal; requires systematically ruling out hypotheses including one tied to a recent infra change"),
    "code-024": ("simple", False, ""),
    # architecture
    "arch-001": ("simple", False, ""),
    "arch-002": ("simple", False, ""),
    "arch-003": ("complex", False, "concurrent editing, conflict resolution, and reconnection semantics must all compose correctly under a tight latency target"),
    "arch-004": ("medium", False, "standard bounded comparison with tradeoffs"),
    "arch-005": ("complex", False, "technical debt, team capability, and zero-downtime/no-freeze constraints all interact in how the migration must be sequenced"),
    "arch-006": ("simple", False, ""),
    "arch-007": ("complex", False, "three distinct attack surfaces (insider, supply chain, log leakage) each need separate domain reasoning"),
    "arch-008": ("simple", False, ""),
    "arch-009": ("simple", False, ""),
    "arch-010": ("complex", False, "dedup, delivery guarantee, and timezone/preference handling must all hold simultaneously at 20M-user scale"),
    "arch-011": ("medium", False, "single-pass explanation with a concrete reasoning chain"),
    "arch-012": ("complex", False, "isolating sync/async latency domains while sharing one auth layer is an interacting-constraint design problem"),
    "arch-013": ("simple", False, ""),
    "arch-014": ("simple", False, ""),
    "arch-015": ("complex", False, "the silent-corruption scenario invalidates naive failover assumptions -- requires a detection and rollback design, not just a runbook"),
    "arch-016": ("simple", False, ""),
    "arch-017": ("complex", False, "explicit CAP-style tradeoff (latency vs. correctness) under a business constraint (no overselling) that recurs weekly"),
    "arch-018": ("simple", False, ""),
    "arch-019": ("medium", False, "requires synthesizing an analogy, single pass"),
    "arch-020": ("complex", False, "tiered permissions, an approval workflow, and an 18-month-later audit requirement must all compose correctly"),
    "arch-021": ("simple", False, ""),
    "arch-022": ("simple", False, ""),
    "arch-023": ("complex", False, "differential freshness requirements and a concurrency fix (thundering herd) must be solved together, not separately"),
    "arch-024": ("simple", False, ""),
    # summarization
    "summ-001": ("simple", False, ""),
    "summ-002": ("simple", False, ""),
    "summ-003": ("complex", False, "risk-based re-ranking (not CVSS), cross-referencing an existing risk register, and per-finding actionability all require judgment beyond compression"),
    "summ-004": ("simple", False, ""),
    "summ-005": ("simple", False, "compression under one constraint (no spoilers), still single-pass"),
    "summ-006": ("simple", False, ""),
    "summ-007": ("simple", False, ""),
    "summ-008": ("complex", False, "adjudicating between three conflicting causal narratives requires structured reasoning, not just compression"),
    "summ-009": ("simple", False, ""),
    "summ-010": ("medium", True, "requires a prioritization judgment (user-facing vs. backend changes) beyond pure compression, but still single-pass summarization"),
    "summ-011": ("simple", False, ""),
    "summ-012": ("complex", False, "cross-document consistency-checking across two long documents on four dimensions is structured comparative analysis, not summarization"),
    # analysis
    "anal-001": ("simple", False, ""),
    "anal-002": ("medium", False, "standard bounded comparison"),
    "anal-003": ("complex", False, "distinguishing a real treatment effect from an instrumentation confound requires designing an analysis, not just interpreting one"),
    "anal-004": ("medium", False, "standard listing with light reasoning"),
    "anal-005": ("complex", False, "adjudicating three competing causal claims from one dataset and naming each one's unaddressed confound"),
    "anal-006": ("simple", False, ""),
    "anal-007": ("complex", False, "organizational history (two failed builds), a stated stakeholder bias, and a scaling timeline all bear on the recommendation"),
    "anal-008": ("simple", False, ""),
    "anal-009": ("simple", False, ""),
    "anal-010": ("complex", False, "tradeoff modeling across three metrics (resolution time, cost, resilience) under an explicit 24/7 operational constraint"),
    "anal-011": ("simple", False, ""),
    "anal-012": ("medium", False, "single-pass explanation drawing on real domain knowledge"),
    "anal-013": ("complex", False, "spotting a cohort-mismatch confound in someone else's comparison and redesigning it correctly"),
    "anal-014": ("simple", False, ""),
    "anal-015": ("simple", False, ""),
    "anal-016": ("complex", False, "the decision framework has to explicitly hold a disputed internal cost estimate alongside reputational and upsell considerations"),
    "anal-017": ("simple", False, ""),
    "anal-018": ("medium", False, "single-pass explanation with one example each"),
    "anal-019": ("complex", False, "reconciling two contradictory metrics requires reasoning about methodology, then advising honest reporting under irreducible uncertainty"),
    "anal-020": ("simple", False, ""),
    "anal-021": ("complex", False, "TCO analysis must incorporate a qualitative key-person departure risk alongside the quantitative cost comparison"),
    "anal-022": ("simple", False, "single well-known fallacy pattern (affirming the consequent), mechanical to spot"),
    "anal-023": ("simple", False, ""),
    "anal-024": ("complex", False, "evaluating sampling-bias validity and diplomatically contesting a stakeholder's decision are two combined judgment tasks"),
}


def main():
    src = Path("eval/candidate_prompts.json")
    dst = Path("eval/labeled_prompts.json")

    data = json.loads(src.read_text(encoding="utf-8"))

    missing = [d["id"] for d in data if d["id"] not in LABELS]
    if missing:
        raise SystemExit(f"Missing labels for: {missing}")

    for d in data:
        tier, borderline, note = LABELS[d["id"]]
        d["true_tier"] = tier
        d["borderline"] = borderline
        d["note"] = note

    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    tiers = Counter(d["true_tier"] for d in data)
    borderline_count = sum(1 for d in data if d["borderline"])
    print("total:", len(data))
    print("tier counts:", dict(tiers))
    print("tier %:", {k: round(100 * v / len(data), 1) for k, v in tiers.items()})
    print("borderline count:", borderline_count)

    by_domain_tier: dict[str, Counter] = {}
    for d in data:
        by_domain_tier.setdefault(d["domain"], Counter())[d["true_tier"]] += 1
    for dom, c in by_domain_tier.items():
        print(dom, dict(c))


if __name__ == "__main__":
    main()
