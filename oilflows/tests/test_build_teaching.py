import json
from pathlib import Path

import pandas as pd
import pytest

from oilflows.build_teaching import (
    EIA_PUBLICATION_LAG_DAYS,
    FLOW_PUBLICATION_LAG_DAYS,
    PRESHOCK_ANCHOR,
    build_checkpoints,
    checkpoint_dates,
)

PUBLISHED = Path(__file__).resolve().parents[1] / "data" / "published"


@pytest.fixture(scope="module")
def daily():
    frame = pd.read_json(PUBLISHED / "oilflows_daily.json")
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    return frame


@pytest.fixture(scope="module")
def buffer():
    return pd.read_csv(PUBLISHED / "us_crude_buffer_weekly.csv")


@pytest.fixture(scope="module")
def payload(daily, buffer):
    return build_checkpoints(
        daily, buffer, generated_at_utc="2026-08-28T00:00:00Z"
    )


def test_checkpoints_are_hindsight_free(daily, payload):
    # Peaks are only definable after the fact; they must never be
    # prediction origins. They live in annotations instead.
    whys = {c["why"] for c in payload["checkpoints"]}
    assert not any("peak" in w.lower() for w in whys)
    labels = {a["label"] for a in payload["annotations"]}
    assert "Brent peak" in labels and "BNO peak" in labels
    assert all(a["note"] == "identifiable only in hindsight"
               for a in payload["annotations"])

    dates = [c["date"] for c in payload["checkpoints"]]
    assert dates == sorted(dates) and len(dates) == len(set(dates))
    assert dates[0] == PRESHOCK_ANCHOR


def test_checkpoints_land_on_observed_market_days(daily, payload):
    rows = daily.set_index("date")
    for c in payload["checkpoints"]:
        # brent/bno as-of dates carry genuine observations, and a
        # weekend month-first is snapped forward, never carried
        assert bool(rows.loc[c["brent_asof"], "brent_observed"])
        assert bool(rows.loc[c["bno_asof"], "bno_observed"])
        if "first market day" in c["why"]:
            assert c["brent_asof"] == c["date"]
            assert c["bno_asof"] == c["date"]


def test_every_value_respects_publication_lag(payload):
    for c in payload["checkpoints"]:
        d = pd.Timestamp(c["date"])
        assert (pd.Timestamp(c["buffer_week_end"])
                + pd.Timedelta(days=EIA_PUBLICATION_LAG_DAYS)) <= d
        assert (pd.Timestamp(c["hormuz_asof"])
                + pd.Timedelta(days=FLOW_PUBLICATION_LAG_DAYS)) <= d
        assert pd.Timestamp(c["brent_asof"]) <= d
        assert pd.Timestamp(c["bno_asof"]) <= d


def test_bypass_outage_zeros_are_treated_as_missing(payload):
    for c in payload["checkpoints"]:
        assert c["yanbu"] != 0.0
        assert c["fujairah"] != 0.0


def test_reads_are_derived_from_the_anchor_not_sim_literals(daily, payload):
    reads = {r["key"]: r for r in payload["reads"]}
    anchor = daily.set_index("date").loc[PRESHOCK_ANCHOR]
    expected = round(float(anchor["brent_spot_last_usd"]) * 1.25, 2)
    assert reads["brent"]["threshold"] == expected
    assert str(expected) in reads["brent"]["label"]
    for r in payload["reads"]:
        assert r["op"] in {"lt", "gt"}
        assert r["field"] in {"hormuz", "yanbu", "buffer", "brent"}


def test_payload_is_strict_json_with_no_narrative_fields(payload):
    text = json.dumps(payload, allow_nan=False, default=float)
    round_trip = json.loads(text)

    for c in round_trip["checkpoints"]:
        # no free-text news field exists in the real schema, by design
        assert "news" not in c
        assert c["brent"] is not None and c["bno"] is not None
        assert c["hormuz"] is not None
        assert c["buffer"] is not None
    last = round_trip["checkpoints"][-1]
    assert last["days_to_next"] is None
    for a, b in zip(round_trip["checkpoints"],
                    round_trip["checkpoints"][1:]):
        gap = (pd.Timestamp(b["date"]) - pd.Timestamp(a["date"])).days
        assert a["days_to_next"] == gap and gap > 0

    blob = text.lower()
    assert "days of oil left" not in blob
    assert "run out" not in blob
    assert "rule-derived" in round_trip["note"]
    assert "revised" in round_trip["revision_note"]
