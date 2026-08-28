import json
from pathlib import Path

import pandas as pd
import pytest

from oilflows.verification import (
    build_current_episode,
    build_verification_publish,
    load_claims,
    load_estimates,
)


CURATED = Path(__file__).resolve().parents[1] / "data" / "curated"


def claims_frame(rows):
    base = {
        "claim_id": "c1",
        "claim_date": "2026-08-19",
        "date_precision": "day",
        "speaker": "U.S. officials",
        "attribution": "anonymous",
        "value_low": 10.0,
        "value_high": 10.0,
        "unit": "mbd",
        "scope": "hormuz_outbound",
        "period": "unspecified",
        "commodity": "unspecified",
        "evidence_type": "government_estimate",
        "quote": "About 10 million barrels per day.",
        "note": "",
        "source_name": "Axios",
        "source_url": "https://example.com/a",
        "entered_date": "2026-08-26",
        "status": "unverified",
        "resolution_note": "",
        "resolution_date": "",
    }
    frame = pd.DataFrame([{**base, **r} for r in rows])
    frame["claim_date"] = pd.to_datetime(frame["claim_date"])
    return frame


def estimates_frame(rows):
    base = {
        "estimate_id": "e1",
        "estimate_date": "2026-08-24",
        "date_precision": "day",
        "tracker": "consensus",
        "value_low": 5.0,
        "value_high": 5.0,
        "value_central": 5.0,
        "unit": "mbd",
        "scope": "hormuz_outbound",
        "period": "unspecified",
        "commodity": "unspecified",
        "evidence_type": "commercial_tracker_model",
        "note": "",
        "as_reported_by": "Reuters",
        "source_url": "https://example.com/b",
        "entered_date": "2026-08-26",
    }
    frame = pd.DataFrame([{**base, **r} for r in rows])
    frame["estimate_date"] = pd.to_datetime(frame["estimate_date"])
    return frame


def test_curated_ledgers_load_and_validate():
    claims = load_claims(CURATED / "hormuz_flow_claims.csv")
    estimates = load_estimates(CURATED / "hormuz_flow_estimates.csv")

    assert len(claims) >= 5
    assert len(estimates) >= 2
    assert (claims["source_url"].str.startswith("http")).all()


def test_invalid_scope_rejected(tmp_path):
    claims = load_claims(CURATED / "hormuz_flow_claims.csv")
    bad = claims.copy()
    bad.loc[0, "scope"] = "vibes"
    path = tmp_path / "bad.csv"
    bad.to_csv(path, index=False)

    with pytest.raises(RuntimeError, match="invalid scope"):
        load_claims(path)


def test_missing_source_url_rejected(tmp_path):
    claims = load_claims(CURATED / "hormuz_flow_claims.csv")
    bad = claims.copy()
    bad.loc[0, "source_url"] = ""
    path = tmp_path / "bad.csv"
    bad.to_csv(path, index=False)

    with pytest.raises(RuntimeError, match="source URL"):
        load_claims(path)


def test_episode_math_matches_memo():
    claims = claims_frame([
        {"claim_id": "c1", "claim_date": "2026-08-01",
         "value_low": 9.0, "value_high": 9.0},
        {"claim_id": "c2", "claim_date": "2026-08-19",
         "value_low": 10.0, "value_high": 10.0},
    ])
    estimates = estimates_frame([
        {"estimate_id": "e1"},
        {"estimate_id": "e2", "estimate_date": "2026-08-01",
         "value_low": 2.0, "value_high": 6.0, "value_central": None},
    ])

    ep = build_current_episode(claims, estimates)

    assert ep["claim_low_mbd"] == 9.0
    assert ep["claim_high_mbd"] == 10.0
    assert ep["independent_consensus_mbd"] == 5.0
    assert ep["independent_low_mbd"] == 2.0
    assert ep["independent_high_mbd"] == 6.0
    assert ep["gap_low_mbd"] == 4.0
    assert ep["gap_high_mbd"] == 5.0
    assert ep["coverage_low_pct"] == 50.0
    assert ep["coverage_high_pct"] == pytest.approx(55.6)
    assert ep["ratio_low"] == 1.8
    assert ep["ratio_high"] == 2.0


def test_cross_scope_and_unit_never_pair():
    # A regional-total claim and a ship-transit count must not enter the
    # hormuz_outbound comparison.
    claims = claims_frame([
        {"claim_id": "c1", "scope": "regional_total_including_bypass",
         "value_low": 15.0, "value_high": 15.0},
        {"claim_id": "c2", "unit": "tankers_per_night",
         "scope": "ship_transits_in_and_out",
         "value_low": 15.0, "value_high": 20.0, "period": "nightly"},
    ])
    estimates = estimates_frame([{"estimate_id": "e1"}])

    assert build_current_episode(claims, estimates) is None

    ep = build_current_episode(
        claims, estimates, scope="regional_total_including_bypass"
    )
    assert ep is None  # no regional-scope estimate exists to compare


def test_stale_claims_fall_out_of_window():
    claims = claims_frame([
        {"claim_id": "c1", "claim_date": "2026-05-01",
         "value_low": 12.0, "value_high": 12.0},
        {"claim_id": "c2", "claim_date": "2026-08-19"},
    ])
    estimates = estimates_frame([{"estimate_id": "e1"}])

    ep = build_current_episode(claims, estimates)
    assert ep["claim_count"] == 1
    assert ep["claim_low_mbd"] == 10.0


def test_publish_payload_is_strict_json():
    claims = load_claims(CURATED / "hormuz_flow_claims.csv")
    estimates = load_estimates(CURATED / "hormuz_flow_estimates.csv")

    payload = build_verification_publish(
        claims, estimates, generated_at_utc="2026-08-26T00:00:00Z"
    )
    text = json.dumps(payload, allow_nan=False)

    round_trip = json.loads(text)
    assert round_trip["current_episode"]["claim_high_mbd"] == 10.0
    assert round_trip["current_episode"]["independent_consensus_mbd"] == 5.0
    assert len(round_trip["claims"]) == len(claims)
    # unverified, never adjudicated language
    assert "unverified" in round_trip["method"]["gap"]
    # statuses are lifecycle states, never adjudication verdicts
    allowed = {
        "unverified", "superseded",
        "consistent_with_independent", "not_corroborated",
    }
    assert all(c["status"] in allowed for c in round_trip["claims"])


def test_archive_ledger_loads_and_links():
    from oilflows.verification import (
        comparable_hormuz_flow_claims,
        load_archive_claims,
    )

    archive = load_archive_claims(CURATED / "us_oil_flow_claims.csv")

    assert len(archive) >= 31
    assert (archive["source_url"].str.startswith("http")).all()

    # history preserved: the deleted escort claim and its same-day dispute.
    # A dispute is a symmetric cross-speaker link, never a supersession —
    # neither side "wins" in the data model.
    escort = archive.loc[archive["claim_id"] == "USOF-20260310-01"].iloc[0]
    assert escort["status"] == "deleted_by_speaker"
    assert pd.isna(escort["superseded_by"])
    assert escort["disputed_by"] == "USOF-20260310-02"

    comparable = comparable_hormuz_flow_claims(archive)
    assert set(comparable["value_min"]) == {8.0, 9.0, 10.0}
    # successive 7-day readings are series members, not corrections
    aug11 = archive.loc[archive["claim_id"] == "USOF-20260811-01"].iloc[0]
    assert pd.isna(aug11["superseded_by"])
    # no credibility-grading verbs anywhere in the descriptions
    assert not archive["claim_text"].str.startswith(
        ("Claimed", "Confirmed")
    ).any()
    # the two-figure planned night is split into one row per figure
    assert "USOF-20260819-04B" in set(archive["claim_id"])
    # rows from one public statement share a rule-derived event id
    ev = archive.set_index("claim_id")["statement_event_id"]
    aug11 = [c for c in archive["claim_id"] if c.startswith("USOF-20260811")]
    assert len(aug11) >= 2
    assert len({ev[c] for c in aug11}) == 1
    assert archive["statement_event_id"].nunique() < len(archive)


def test_archive_rejects_dangling_supersedes(tmp_path):
    from oilflows.verification import load_archive_claims

    frame = pd.read_csv(CURATED / "us_oil_flow_claims.csv", dtype=str)
    frame.loc[0, "supersedes_claim_id"] = "USOF-DOES-NOT-EXIST"
    path = tmp_path / "bad.csv"
    frame.to_csv(path, index=False)

    with pytest.raises(RuntimeError, match="unknown claims"):
        load_archive_claims(path)


def test_site_ledger_covers_archive_comparable_claims():
    # Every directly comparable archive claim must appear in the site
    # ledger with the same value, so the episode math never lags the
    # historical record.
    from oilflows.verification import (
        comparable_hormuz_flow_claims,
        load_archive_claims,
    )

    archive = load_archive_claims(CURATED / "us_oil_flow_claims.csv")
    site = load_claims(CURATED / "hormuz_flow_claims.csv")

    comparable = comparable_hormuz_flow_claims(archive)
    site_vals = set(
        site.loc[
            (site["scope"] == "hormuz_outbound") & (site["unit"] == "mbd"),
            "value_high",
        ]
    )
    missing = set(comparable["value_max"]) - site_vals
    assert not missing, f"archive claims absent from site ledger: {missing}"


def test_episode_reflects_wright_revision():
    claims = load_claims(CURATED / "hormuz_flow_claims.csv")
    estimates = load_estimates(CURATED / "hormuz_flow_estimates.csv")

    ep = build_current_episode(claims, estimates)
    assert ep["claim_low_mbd"] == 8.0
    assert ep["claim_high_mbd"] == 10.0
    assert ep["gap_low_mbd"] == 3.0
    assert ep["gap_high_mbd"] == 5.0
