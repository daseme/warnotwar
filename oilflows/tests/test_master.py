import pandas as pd

from oilflows.master import build_daily_master


def make_inputs():
    dates = pd.date_range("2025-07-01", periods=14, freq="D")

    hormuz = pd.DataFrame({
        "date": dates,
        "hormuz_tanker_count": 10.0,
        "hormuz_tanker_count_7d": 10.0,
        "hormuz_tanker_capacity": 100.0,
        "hormuz_tanker_capacity_7d": 100.0,
    })

    iraq = pd.DataFrame({
        "date": dates,
        "iraq_basrah_mbd": 3.0,
        "iraq_basrah_7d_mbd": 3.0,
        "allocation_method": "official_portwatch_weighted",
        "calibration_source": "SOMO",
    })

    kuwait = pd.DataFrame({
        "date": dates,
        "kuwait_crude_mbd": 1.0,
        "kuwait_crude_7d_mbd": 1.0,
        "allocation_method": "official_portwatch_weighted",
        "calibration_source": "JODI",
    })

    saudi = pd.DataFrame({
        "date": dates,
        "saudi_official_crude_mbd": 6.0,
        "saudi_gulf_juaymah_proxy_mt": 100.0,
        "saudi_gulf_juaymah_proxy_mt_7d": 100.0,
        "saudi_bypass_yanbu_proxy_mt": 50.0,
        "saudi_bypass_yanbu_proxy_mt_7d": 50.0,
        "saudi_proxy_bypass_share_7d": 1/3,
        "saudi_official_status": "official_jodi_monthly_flat",
    })

    uae = pd.DataFrame({
        "date": dates,
        "uae_gulf_proxy_mt_7d": 100.0,
        "uae_bypass_fujairah_proxy_mt_7d": 50.0,
        "uae_gulf_proxy_index_7d": 100.0,
        "uae_bypass_proxy_index_7d": 100.0,
        "uae_proxy_bypass_share_7d": 1/3,
        "uae_official_status": "proxy_only_no_jodi_export_volume",
    })

    return hormuz, iraq, kuwait, saudi, uae


def test_master_composites_are_correct():
    inputs = make_inputs()
    result = build_daily_master(
        *inputs,
        start_date="2025-07-01",
        baseline_start="2025-07-01",
        baseline_end="2025-07-14",
    )

    row = result.iloc[-1]
    assert row["known_gulf_official_mbd"] == 4.0
    assert row["known_gulf_official_7d_mbd"] == 4.0
    assert row["core_official_exports_mbd"] == 10.0
    assert row["core_official_exports_7d_mbd"] == 10.0


def test_master_baseline_indices_equal_100_for_constant_series():
    inputs = make_inputs()
    result = build_daily_master(
        *inputs,
        start_date="2025-07-01",
        baseline_start="2025-07-01",
        baseline_end="2025-07-14",
    )

    row = result.iloc[-1]
    assert row["hormuz_tanker_count_index_7d"] == 100.0
    assert row["known_gulf_official_index_7d"] == 100.0
    assert row["core_official_exports_index_7d"] == 100.0
    assert row["saudi_gulf_proxy_index_7d"] == 100.0
    assert row["saudi_bypass_proxy_index_7d"] == 100.0


def test_master_marks_core_completeness():
    inputs = list(make_inputs())
    inputs[1].loc[0, "iraq_basrah_mbd"] = float("nan")

    result = build_daily_master(
        *inputs,
        start_date="2025-07-01",
        baseline_start="2025-07-01",
        baseline_end="2025-07-14",
    )

    assert not bool(result.iloc[0]["official_core_complete"])
    assert bool(result.iloc[-1]["official_core_complete"])
