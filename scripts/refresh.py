import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from career_tracker.refresh import refresh


def main():
    parser = argparse.ArgumentParser(description="Refresh official job sources for the Global AI Career Tracker")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "tracker.json")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "jobs.json")
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "refresh-report.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report = refresh(config["sources"], args.data, args.report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
