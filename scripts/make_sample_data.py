"""Write an example night to sample_data/sample_night.csv.

The file shows the CSV format the import endpoint expects. It is produced by
the same synthetic generator the app uses for demo data, with the true sleep
stage removed - the app has to work that out by itself.

Run from the repository root:   python scripts/make_sample_data.py
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.synthetic import generate_nights  # noqa: E402

OUT = ROOT / "sample_data" / "sample_night.csv"


def main() -> None:
    night = generate_nights(1, seed=11, last_night=date(2026, 3, 2))[0]
    data = night["data"].drop(columns=["stage_true"])
    data["timestamp"] = data["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data.round(1).to_csv(OUT, index=False)
    print(f"Wrote {len(data)} rows to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
