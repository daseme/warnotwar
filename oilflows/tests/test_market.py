import pandas as pd

from oilflows.market import (
    add_market_calendar_features,
    parse_bno_yahoo,
    parse_fred_brent,
)


def test_parse_fred_brent_accepts_observation_date():
    text = (
        "observation_date,DCOILBRENTEU\n"
        "2026-01-01,75.10\n"
        "2026-01-02,.\n"
    )
    result = parse_fred_brent(text)

    assert result.iloc[0]["brent_spot_usd"] == 75.10
    assert pd.isna(result.iloc[1]["brent_spot_usd"])


def test_parse_bno_yahoo_keeps_unadjusted_close():
    payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "timestamp": [1767283200, 1767369600],
                    "indicators": {
                        "quote": [
                            {
                                "close": [30.0, 31.0],
                                "volume": [100, 200],
                            }
                        ],
                        "adjclose": [
                            {"adjclose": [29.5, 30.5]}
                        ],
                    },
                }
            ],
        }
    }

    result = parse_bno_yahoo(payload)

    assert result["bno_close_usd"].tolist() == [30.0, 31.0]
    assert result["bno_adj_close_usd"].tolist() == [29.5, 30.5]


def test_market_calendar_features_forward_fill_last_close_only():
    market = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-02", "2026-01-05"]),
            "brent_spot_usd": [75.0, 76.0],
            "bno_close_usd": [30.0, 31.0],
            "bno_adj_close_usd": [30.0, 31.0],
            "bno_volume": [100, 200],
        }
    )

    result = add_market_calendar_features(
        market,
        start_date="2026-01-02",
        end_date="2026-01-05",
    )

    weekend = result.loc[
        result["date"].eq(pd.Timestamp("2026-01-03"))
    ].iloc[0]

    assert pd.isna(weekend["bno_close_usd"])
    assert weekend["bno_last_close_usd"] == 30.0
    assert not bool(weekend["bno_observed"])
