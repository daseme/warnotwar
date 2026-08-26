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
    assert all(
        c["status"] == "unverified" for c in round_trip["claims"]
    )
