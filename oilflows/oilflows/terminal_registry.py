from dataclasses import dataclass
from difflib import SequenceMatcher

import pandas as pd


@dataclass(frozen=True)
class TerminalSeed:
    country: str
    search_name: str
    role: str
    include_group: str


# Candidate terminals for PortWatch discovery.
#
# Important: this list is intentionally broader than the final production
# whitelist. resolve_terminal_candidates() only ranks possible PortWatch
# matches; it does not auto-approve any terminal.
#
# Roles containing "diagnostic" or "low_confidence" are deliberately kept
# separate from the core Gulf crude aggregate until their historical daily
# series have been inspected.
TERMINAL_SEEDS = (
    # Saudi Arabia — Persian Gulf crude-loading terminals.
    TerminalSeed("Saudi Arabia", "Ras Tanura", "gulf_crude", "saudi_gulf"),
    TerminalSeed("Saudi Arabia", "Juaymah", "gulf_crude", "saudi_gulf"),

    # Saudi Arabia — Red Sea bypass terminal for East-West Pipeline barrels.
    # Do not use generic "Yanbu"; PortWatch also has a separate Yanbu city port.
    TerminalSeed(
        "Saudi Arabia",
        "King Fahd Port",
        "bypass_crude",
        "saudi_bypass",
    ),

    # Kuwait.
    TerminalSeed("Kuwait", "Mina Al Ahmadi", "gulf_crude", "kuwait_gulf"),

    # United Arab Emirates — inside-Hormuz crude-loading candidates.
    TerminalSeed(
        "United Arab Emirates",
        "Jabal Az Zannah-Ruways",
        "gulf_crude",
        "uae_gulf",
    ),
    TerminalSeed(
        "United Arab Emirates",
        "Das Island",
        "gulf_crude_condensate",
        "uae_gulf",
    ),
    TerminalSeed(
        "United Arab Emirates",
        "Zirku Island",
        "gulf_crude_candidate",
        "uae_gulf",
    ),

    # United Arab Emirates — outside-Hormuz bypass/export hub. Fujairah is a
    # mixed liquids port, so treat its PortWatch series as a proxy rather than
    # pure crude until calibrated/validated.
    TerminalSeed(
        "United Arab Emirates",
        "Fujairah",
        "bypass_crude_mixed_proxy",
        "uae_bypass",
    ),

    # Iraq — PortWatch exposes both the city/port concept and the offshore oil
    # terminal. Pull both as diagnostics; only the actual loading-terminal
    # series should enter the production crude aggregate if the daily history
    # proves usable.
    TerminalSeed(
        "Iraq",
        "Basrah Oil Terminal",
        "gulf_crude_candidate",
        "iraq_gulf",
    ),
    TerminalSeed(
        "Iraq",
        "Al Basrah",
        "diagnostic_portwatch_aggregate",
        "iraq_diagnostic",
    ),

    # Iran — core and secondary crude-loading candidates.
    TerminalSeed("Iran", "Kharg Island", "gulf_crude", "iran_gulf"),
    TerminalSeed("Iran", "Lavan", "gulf_crude_candidate", "iran_gulf"),
    TerminalSeed(
        "Iran",
        "Bahregan",
        "diagnostic_crude_candidate",
        "iran_diagnostic",
    ),

    # Iran — Gulf of Oman bypass candidate, outside Hormuz.
    TerminalSeed("Iran", "Jask", "bypass_crude_candidate", "iran_bypass"),

    # Qatar — PortWatch does not expose Halul Island, Qatar's key offshore
    # crude export terminal. Keep these available for inspection, but do not
    # treat them as complete Qatar crude coverage.
    TerminalSeed(
        "Qatar",
        "Doha-Umm Said",
        "low_confidence_crude_mixed",
        "qatar_diagnostic",
    ),
    TerminalSeed(
        "Qatar",
        "Ras Laffan",
        "low_confidence_condensate_mixed",
        "qatar_diagnostic",
    ),
)


def resolve_terminal_candidates(
    registry: pd.DataFrame,
    seeds: tuple[TerminalSeed, ...] = TERMINAL_SEEDS,
    candidates_per_seed: int = 5,
) -> pd.DataFrame:
    """Return ranked PortWatch matches; this does not silently auto-approve terminals."""
    rows: list[dict[str, object]] = []

    for seed in seeds:
        country_rows = registry.loc[registry["country"].fillna("").eq(seed.country)].copy()
        if country_rows.empty:
            rows.append(_missing_seed_row(seed))
            continue

        country_rows["match_score"] = country_rows["portname"].fillna("").map(
            lambda name: name_similarity(seed.search_name, str(name))
        )
        ranked = country_rows.sort_values(
            ["match_score", "vessel_count_tanker"], ascending=[False, False]
        ).head(candidates_per_seed)

        for rank, (_, candidate) in enumerate(ranked.iterrows(), start=1):
            rows.append(
                {
                    "seed_country": seed.country,
                    "seed_search_name": seed.search_name,
                    "role": seed.role,
                    "include_group": seed.include_group,
                    "candidate_rank": rank,
                    "match_score": round(float(candidate["match_score"]), 4),
                    "portid": candidate.get("portid"),
                    "portname": candidate.get("portname"),
                    "fullname": candidate.get("fullname"),
                    "LOCODE": candidate.get("LOCODE"),
                    "lat": candidate.get("lat"),
                    "lon": candidate.get("lon"),
                    "vessel_count_tanker": candidate.get("vessel_count_tanker"),
                    "industry_top1": candidate.get("industry_top1"),
                    "industry_top2": candidate.get("industry_top2"),
                    "industry_top3": candidate.get("industry_top3"),
                    "approved": "",
                }
            )

    return pd.DataFrame(rows)


def name_similarity(expected: str, actual: str) -> float:
    return SequenceMatcher(None, normalize_name(expected), normalize_name(actual)).ratio()


def normalize_name(value: str) -> str:
    return " ".join(
        value.lower()
        .replace("-", " ")
        .replace("/", " ")
        .replace("'", "")
        .replace("’", "")
        .split()
    )


def _missing_seed_row(seed: TerminalSeed) -> dict[str, object]:
    return {
        "seed_country": seed.country,
        "seed_search_name": seed.search_name,
        "role": seed.role,
        "include_group": seed.include_group,
        "candidate_rank": None,
        "match_score": None,
        "portid": None,
        "portname": None,
        "fullname": None,
        "LOCODE": None,
        "lat": None,
        "lon": None,
        "vessel_count_tanker": None,
        "industry_top1": None,
        "industry_top2": None,
        "industry_top3": None,
        "approved": "",
    }
