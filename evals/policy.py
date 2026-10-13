"""Regression policy for eval runs (see evals/REGRESSION.md). Pure functions, no I/O, unit-tested.

- Deterministic checks (execution, structured, provenance P1) are hard-blocking on a single run.
- A commentary claim that FAILs now but PASSed in the baseline (a "flip"; a claim absent from the baseline counts
  as a flip) triggers RESAMPLES more runs of that case. The case's claims are then judged on all samples:
    fails >= 2 -> FAIL (blocks) | fails == 1 -> UNSTABLE (reported, not blocking) | 0 -> PASS.
  A claim the grader could not judge in some sample (BLOCKED) never counts as a pass: 0 fails + any BLOCKED -> BLOCKED.
"""
RESAMPLES = 3          # extra runs on a flip, so a flipped case is judged on 1 + 3 = 4 samples
BLOCK_AT_FAILS = 2     # this many failing samples (or more) blocks
DETERMINISTIC_GROUPS = ("execution", "structured", "provenance")


def deterministic_ok(result):
    """True if every execution/structured/provenance check in a single-sample result PASSed."""
    return all(c["status"] == "PASS" for g in DETERMINISTIC_GROUPS for c in result.get(g, []))


def flipped_claims(claims, baseline_claims):
    """Claim ids that FAIL now and PASSed in the baseline (or have no baseline record).
    claims: [{'id', 'status', ...}]; baseline_claims: {claim_id: status} or None (no baseline -> every FAIL is a flip)."""
    flips = []
    for c in claims:
        if c["status"] != "FAIL":
            continue
        before = (baseline_claims or {}).get(c["id"])
        if before is None or before == "PASS":
            flips.append(c["id"])
    return flips


def should_resample(result, baseline_claims):
    """Resample only for commentary flips, and only when the deterministic checks passed (else it is blocked anyway)."""
    return deterministic_ok(result) and bool(flipped_claims(result.get("commentary", []), baseline_claims))


def judge_claims(samples):
    """samples: list of claim lists (one per sample). Returns {claim_id: {...}} with counts, pass rate and status."""
    out = {}
    for sample in samples:
        for c in sample:
            j = out.setdefault(c["id"], {"id": c["id"], "kind": c.get("kind"), "claim": c.get("claim"),
                                         "passes": 0, "fails": 0, "blocked": 0, "samples": 0, "evidence": []})
            j["samples"] += 1
            key = {"PASS": "passes", "FAIL": "fails"}.get(c["status"], "blocked")
            j[key] += 1
            j["evidence"].append({"status": c["status"], "evidence": c.get("evidence", "")})
    for j in out.values():
        j["pass_rate"] = f"{j['passes']}/{j['samples']}"
        j["status"] = ("FAIL" if j["fails"] >= BLOCK_AT_FAILS else
                       "UNSTABLE" if j["fails"] == 1 else
                       "BLOCKED" if j["blocked"] else "PASS")
    return out


def case_verdict(sample_results, claim_judgments):
    """Overall case status after resampling: any deterministic FAIL in any sample -> FAIL; any claim FAIL -> FAIL;
    any BLOCKED -> BLOCKED; any UNSTABLE -> UNSTABLE; else PASS."""
    det = [c["status"] for r in sample_results for g in DETERMINISTIC_GROUPS for c in r.get(g, [])]
    claims = [j["status"] for j in claim_judgments.values()]
    if "FAIL" in det or "FAIL" in claims:
        return "FAIL"
    if "BLOCKED" in det or "BLOCKED" in claims:
        return "BLOCKED"
    if "UNSTABLE" in claims:
        return "UNSTABLE"
    return "PASS"
