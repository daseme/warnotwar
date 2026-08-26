from __future__ import annotations

import pandas as pd


# Claims and estimates are hand-curated journalism data: every row must
# carry a dated, linked source. Scopes are enforced so that unlike
# quantities (Hormuz-only vs regional-with-bypass vs ship transits) can
# never be compared to each other in code.

SCOPES = {
    "hormuz_outbound",
    "regional_total_including_bypass",
    "ship_transits_in_and_out",
}

UNITS = {"mbd", "tankers_per_night", "mbbl_single_day"}

PERIODS = {"seven_day_average", "single_day", "nightly", "unspecified"}

# What is being counted. Sources rarely say; "unspecified" is itself a
# finding — most circulating numbers never state their commodity scope.
COMMODITIES = {"crude", "crude_condensate", "all_liquids", "unspecified"}

EVIDENCE_TYPES = {
    "government_estimate",
    "commercial_tracker_model",
    "activity_index",
    "official_ledger",
}

ATTRIBUTIONS = {"named", "anonymous", "institutional"}

DATE_PRECISIONS = {"day", "month"}

# unverified: no independent corroboration yet (the default).
# consistent_with_independent: later data matched the claim.
# not_corroborated: later data failed to support the claim.
# superseded: the speaker (or their institution) issued a newer figure.
CLAIM_STATUSES = {
    "unverified", "consistent_with_independent", "not_corroborated",
    "superseded",
}

# The archive ledger (us_oil_flow_claims.csv) is the full historical record
# of U.S. statements, deliberately looser than the site ledger: it preserves
# nuance (free-text channels, rich time bases) and never overwrites history.
# Strictness lives in the comparable view derived from it.
ARCHIVE_ATTRIBUTIONS = {"named", "anonymous", "institutional"}
ARCHIVE_STATUSES = {"active", "corrected", "retracted_and_denied", "superseded"}

# Claims within this window of the anchor date count as "current".
EPISODE_WINDOW_DAYS = 45


def load_claims(path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str)
    required = {
        "claim_id", "claim_date", "date_precision", "speaker",
        "attribution", "value_low", "value_high", "unit", "scope",
        "period", "commodity", "evidence_type", "quote",
        "source_name", "source_url", "status",
    }
    _require_columns(frame, required, "claims")

    _validate_enum(frame, "scope", SCOPES, "claims")
    _validate_enum(frame, "unit", UNITS, "claims")
    _validate_enum(frame, "period", PERIODS, "claims")
    _validate_enum(frame, "commodity", COMMODITIES, "claims")
    _validate_enum(frame, "evidence_type", EVIDENCE_TYPES, "claims")
    _validate_enum(frame, "attribution", ATTRIBUTIONS, "claims")
    _validate_enum(frame, "date_precision", DATE_PRECISIONS, "claims")
    _validate_enum(frame, "status", CLAIM_STATUSES, "claims")
    _validate_sources(frame, "claims")

    frame["claim_date"] = pd.to_datetime(frame["claim_date"], errors="raise")
    for column in ("value_low", "value_high"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    if frame["claim_id"].duplicated().any():
        raise RuntimeError("Duplicate claim_id in claims ledger.")
    if (frame["value_low"] > frame["value_high"]).any():
        raise RuntimeError("Claims ledger has value_low > value_high.")

    return frame.sort_values("claim_date").reset_index(drop=True)


def load_estimates(path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str)
    required = {
        "estimate_id", "estimate_date", "date_precision", "tracker",
        "value_low", "value_high", "value_central", "unit", "scope",
        "period", "commodity", "evidence_type",
        "as_reported_by", "source_url",
    }
    _require_columns(frame, required, "estimates")

    _validate_enum(frame, "scope", SCOPES, "estimates")
    _validate_enum(frame, "unit", UNITS, "estimates")
    _validate_enum(frame, "period", PERIODS, "estimates")
    _validate_enum(frame, "commodity", COMMODITIES, "estimates")
    _validate_enum(frame, "evidence_type", EVIDENCE_TYPES, "estimates")
    _validate_enum(frame, "date_precision", DATE_PRECISIONS, "estimates")
    _validate_sources(frame, "estimates", url_column="source_url")

    if frame["as_reported_by"].isna().any():
        raise RuntimeError(
            "Estimates ledger has rows without as_reported_by: tracker "
            "figures reach us secondhand and the reporting outlet must "
            "be named."
        )

    frame["estimate_date"] = pd.to_datetime(
        frame["estimate_date"], errors="raise"
    )
    for column in ("value_low", "value_high", "value_central"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame["estimate_id"].duplicated().any():
        raise RuntimeError("Duplicate estimate_id in estimates ledger.")

    return frame.sort_values("estimate_date").reset_index(drop=True)


def load_archive_claims(path) -> pd.DataFrame:
    """Load the full historical U.S.-statements ledger.

    Validation is pragmatic: identity, dates, sources and the small enums
    are enforced; descriptive fields (channel, commodity, metric,
    time_basis) stay free-form to preserve nuance. History is never
    rewritten — corrections and supersessions are links, not edits.
    """
    frame = pd.read_csv(path, dtype=str)
    required = {
        "claim_id", "statement_date", "speaker", "attribution", "scope",
        "direction", "unit", "time_basis", "claim_text", "status",
        "supersedes_claim_id", "source_publisher", "source_url",
        "value_min", "value_max",
    }
    _require_columns(frame, required, "archive")

    _validate_enum(frame, "attribution", ARCHIVE_ATTRIBUTIONS, "archive")
    _validate_enum(frame, "status", ARCHIVE_STATUSES, "archive")
    _validate_sources(frame, "archive")

    if frame["claim_id"].duplicated().any():
        raise RuntimeError("Duplicate claim_id in archive ledger.")
    frame["statement_date"] = pd.to_datetime(
        frame["statement_date"], errors="raise"
    )
    for column in ("value_min", "value_max"):
        # empty means unstated / open-ended (e.g. "more than 100 million")
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    known = set(frame["claim_id"])
    dangling = frame.loc[
        frame["supersedes_claim_id"].notna()
        & ~frame["supersedes_claim_id"].isin(known),
        "supersedes_claim_id",
    ]
    if not dangling.empty:
        raise RuntimeError(
            f"Archive supersedes links point at unknown claims: "
            f"{sorted(dangling)}"
        )

    superseded_by = frame.dropna(subset=["supersedes_claim_id"]).set_index(
        "supersedes_claim_id"
    )["claim_id"]
    frame["superseded_by"] = frame["claim_id"].map(superseded_by)

    return frame.sort_values("statement_date").reset_index(drop=True)


def comparable_hormuz_flow_claims(archive: pd.DataFrame) -> pd.DataFrame:
    """Only directly comparable outbound Hormuz oil-flow-rate claims in
    million barrels/day — the apples-to-apples series."""
    return archive.loc[
        (archive["scope"] == "hormuz_only")
        & (archive["direction"] == "outbound")
        & (archive["unit"] == "million_barrels_per_day")
    ].reset_index(drop=True)


def build_current_episode(
    claims: pd.DataFrame,
    estimates: pd.DataFrame,
    *,
    scope: str = "hormuz_outbound",
    window_days: int = EPISODE_WINDOW_DAYS,
) -> dict | None:
    """Compare like with like: latest rate claims vs rate estimates,
    one scope, one unit, one time window.

    Anchored to the newest ledger date rather than the wall clock so a
    rebuild months later reports the same episode, not a shifted window.
    Returns None when either side of the comparison is missing.
    """
    if scope not in SCOPES:
        raise RuntimeError(f"Unknown scope {scope!r}.")

    rate_claims = claims.loc[
        (claims["scope"] == scope) & (claims["unit"] == "mbd")
    ]
    rate_estimates = estimates.loc[
        (estimates["scope"] == scope) & (estimates["unit"] == "mbd")
    ]
    if rate_claims.empty or rate_estimates.empty:
        return None

    anchor = max(
        rate_claims["claim_date"].max(),
        rate_estimates["estimate_date"].max(),
    )
    cutoff = anchor - pd.Timedelta(days=window_days)
    window_claims = rate_claims.loc[rate_claims["claim_date"] >= cutoff]
    window_estimates = rate_estimates.loc[
        rate_estimates["estimate_date"] >= cutoff
    ]
    if window_claims.empty or window_estimates.empty:
        return None

    claim_low = float(window_claims["value_low"].min())
    claim_high = float(window_claims["value_high"].max())

    est_low = float(window_estimates["value_low"].min())
    est_high = float(window_estimates["value_high"].max())
    with_central = window_estimates.dropna(subset=["value_central"])
    consensus = (
        float(with_central.iloc[-1]["value_central"])
        if not with_central.empty
        else None
    )

    episode = {
        "scope": scope,
        "as_of": anchor.date().isoformat(),
        "window_days": window_days,
        "claim_low_mbd": claim_low,
        "claim_high_mbd": claim_high,
        "claim_count": int(len(window_claims)),
        "independent_low_mbd": est_low,
        "independent_high_mbd": est_high,
        "independent_consensus_mbd": consensus,
        "estimate_count": int(len(window_estimates)),
    }

    if consensus and consensus > 0:
        episode.update(
            {
                "gap_low_mbd": round(claim_low - consensus, 2),
                "gap_high_mbd": round(claim_high - consensus, 2),
                "coverage_low_pct": round(100 * consensus / claim_high, 1),
                "coverage_high_pct": round(100 * consensus / claim_low, 1),
                "ratio_low": round(claim_low / consensus, 2),
                "ratio_high": round(claim_high / consensus, 2),
            }
        )

    return episode


def build_verification_publish(
    claims: pd.DataFrame,
    estimates: pd.DataFrame,
    *,
    generated_at_utc: str | None = None,
) -> dict:
    if generated_at_utc is None:
        generated_at_utc = (
            pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def records(frame: pd.DataFrame, date_column: str) -> list[dict]:
        out = frame.copy()
        out[date_column] = out[date_column].dt.strftime("%Y-%m-%d")
        out = out.astype(object).where(pd.notna(out), None)
        return out.to_dict(orient="records")

    return {
        "schema_version": 1,
        "generated_at_utc": generated_at_utc,
        "current_episode": build_current_episode(claims, estimates),
        "claims": records(claims, "claim_date"),
        "estimates": records(estimates, "estimate_date"),
        "scope_definitions": {
            "hormuz_outbound":
                "Oil claimed or estimated to be exiting through the Strait "
                "of Hormuz itself.",
            "regional_total_including_bypass":
                "Hormuz flow plus bypass pipelines and export routes; not "
                "comparable to Hormuz-only figures.",
            "ship_transits_in_and_out":
                "Vessel transits counted in both directions; includes "
                "empty inbound ships, so not a loaded-outbound count.",
        },
        "method": {
            "gap":
                "The verification gap is the claimed flow minus the "
                "independent tracker consensus, computed only within one "
                "scope, one unit, and one time window. It is labeled "
                "unverified, not false.",
            "estimates_provenance":
                "Independent tracker figures reach this dataset secondhand, "
                "as reported by the named press outlet on each row.",
            "resolution":
                "The gap can only be resolved retrospectively: Gulf "
                "loadings, destination arrivals and official trade data. "
                "First referee: official Iraq/Kuwait/Saudi export figures "
                "for August 2026, expected around October-November 2026, "
                "already tracked by this site's official-tally instrument.",
            "dark_transits":
                "Ships operating without AIS may explain part of the gap "
                "(a tracker undercount). A missed VLCC is roughly 2 "
                "million barrels. The explanation cuts both ways and is "
                "not adjudicated here.",
        },
        "guardrails": [
            "The difference is labeled unverified, never lying or "
            "exaggeration.",
            "Comparisons never cross scopes or units.",
            "Anonymous attributions are marked as such.",
            "PortWatch activity indices are never converted into "
            "barrels-per-day estimates.",
            "Every value carries a dated, linked source.",
        ],
    }


def _require_columns(frame: pd.DataFrame, required: set, name: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"{name} ledger missing columns: {missing}")


def _validate_enum(
    frame: pd.DataFrame, column: str, allowed: set, name: str
) -> None:
    bad = sorted(set(frame[column].dropna()) - allowed)
    if bad or frame[column].isna().any():
        raise RuntimeError(
            f"{name} ledger has invalid {column} values: "
            f"{bad or ['<missing>']} (allowed: {sorted(allowed)})"
        )


def _validate_sources(
    frame: pd.DataFrame, name: str, *, url_column: str = "source_url"
) -> None:
    urls = frame[url_column].fillna("")
    if (~urls.str.startswith("http")).any():
        raise RuntimeError(
            f"{name} ledger has rows without a linked source URL."
        )
