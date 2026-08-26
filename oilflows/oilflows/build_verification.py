from pathlib import Path
import json

from .verification import (
    build_verification_publish,
    load_claims,
    load_estimates,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    curated = project_root / "data" / "curated"
    published = project_root / "data" / "published"
    published.mkdir(parents=True, exist_ok=True)

    claims = load_claims(curated / "hormuz_flow_claims.csv")
    estimates = load_estimates(curated / "hormuz_flow_estimates.csv")

    payload = build_verification_publish(claims, estimates)

    out_path = published / "hormuz_verification.json"
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )

    print(f"Claims: {len(claims)}  Estimates: {len(estimates)}")
    print(f"Wrote {out_path}")

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
