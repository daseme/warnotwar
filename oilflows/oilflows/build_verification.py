from pathlib import Path
import json

import pandas as pd

from .verification import (
    build_verification_publish,
    comparable_hormuz_flow_claims,
    load_archive_claims,
    load_claims,
    load_estimates,
)


def archive_records(frame: pd.DataFrame) -> list[dict]:
    out = frame.copy()
    out["statement_date"] = out["statement_date"].dt.strftime("%Y-%m-%d")
    out = out.astype(object).where(pd.notna(out), None)
    return out.to_dict(orient="records")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    curated = project_root / "data" / "curated"
    published = project_root / "data" / "published"
    published.mkdir(parents=True, exist_ok=True)

    claims = load_claims(curated / "hormuz_flow_claims.csv")
    estimates = load_estimates(curated / "hormuz_flow_estimates.csv")
    archive = load_archive_claims(curated / "us_oil_flow_claims.csv")

    payload = build_verification_publish(claims, estimates)

    out_path = published / "hormuz_verification.json"
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )

    comparable = comparable_hormuz_flow_claims(archive)
    archive_payload = {
        "schema_version": 1,
        "generated_at_utc": payload["generated_at_utc"],
        "first_statement": archive["statement_date"].min().date().isoformat(),
        "last_statement": archive["statement_date"].max().date().isoformat(),
        "claim_count": int(len(archive)),
        "notes": [
            "Full historical ledger of reported U.S. government statements "
            "about oil and vessel movement through Hormuz and Gulf bypass "
            "routes. History is never overwritten: corrections, denials and "
            "supersessions are preserved as linked rows.",
            "Not guaranteed complete: statements occur in gaggles, "
            "interviews, deleted posts and anonymous briefings. See the "
            "collection protocol in US_OIL_FLOW_CLAIMS_DATABASE_BRIEF.md.",
        ],
        "comparable_hormuz_flow_claim_ids":
            comparable["claim_id"].tolist(),
        "claims": archive_records(archive),
    }
    archive_path = published / "us_oil_flow_claims.json"
    archive_path.write_text(
        json.dumps(
            archive_payload, indent=2, ensure_ascii=False, allow_nan=False
        ),
        encoding="utf-8",
    )

    print(f"Claims: {len(claims)}  Estimates: {len(estimates)}")
    print(
        f"Archive: {len(archive)} statements "
        f"({archive_payload['first_statement']} .. "
        f"{archive_payload['last_statement']}), "
        f"{len(comparable)} directly comparable Hormuz flow-rate claims"
    )
    print(f"Wrote {out_path}")
    print(f"Wrote {archive_path}")

    episode = payload["current_episode"]
    if episode:
        print(
            f"\nCurrent episode ({episode['scope']}, as of {episode['as_of']}):"
        )
        print(
            f"  claimed {episode['claim_low_mbd']:g}-"
            f"{episode['claim_high_mbd']:g} mb/d vs independent "
            f"{episode['independent_consensus_mbd']:g} mb/d "
            f"(range {episode['independent_low_mbd']:g}-"
            f"{episode['independent_high_mbd']:g})"
        )
        if "gap_low_mbd" in episode:
            print(
                f"  unverified {episode['gap_low_mbd']:g}-"
                f"{episode['gap_high_mbd']:g} mb/d; coverage "
                f"{episode['coverage_low_pct']:g}-"
                f"{episode['coverage_high_pct']:g}%; claim/observed "
                f"{episode['ratio_low']:g}-{episode['ratio_high']:g}x"
            )
    else:
        print("\nNo comparable current episode (missing claims or estimates).")


if __name__ == "__main__":
    main()
