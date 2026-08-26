import pandas as pd

from oilflows.terminal_registry import TerminalSeed, name_similarity, resolve_terminal_candidates


def test_name_similarity_prefers_expected_port():
    assert name_similarity("Ras Tanura", "Ras Tanura") > name_similarity("Ras Tanura", "Jeddah")


def test_resolve_candidates_ranks_best_match_first():
    registry = pd.DataFrame(
        [
            {"portid": "P1", "portname": "Jubail", "country": "Saudi Arabia", "vessel_count_tanker": 20},
            {"portid": "P2", "portname": "Ras Tanura", "country": "Saudi Arabia", "vessel_count_tanker": 30},
        ]
    )
    seeds = (TerminalSeed("Saudi Arabia", "Ras Tanura", "gulf_crude", "saudi_gulf"),)

    result = resolve_terminal_candidates(registry, seeds=seeds, candidates_per_seed=2)

    assert result.iloc[0]["portid"] == "P2"
    assert result.iloc[0]["portname"] == "Ras Tanura"
