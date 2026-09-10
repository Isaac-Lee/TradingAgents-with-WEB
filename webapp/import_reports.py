"""Import Alpha-Ledger or local report folders without altering source captures."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from .service import JobStore, now


def import_reports(store, checkout=None, *, folders=None):
    from tradingagents.agents.utils.rating import extract_rating

    local = folders is not None
    revision = None
    if local:
        folders = [Path(folder).resolve() for folder in folders]
        for folder in folders:
            if not folder.is_dir() or not (folder / "complete_report.md").is_file():
                raise ValueError(f"Missing report folder or complete_report.md: {folder}")
            if not re.fullmatch(r"(.+)_(\d{4})(\d{2})(\d{2})(?:_\d+)?", folder.name):
                raise ValueError(f"Expected SYMBOL_YYYYMMDD report folder: {folder}")
    else:
        checkout = Path(checkout).resolve()
        revision = subprocess.check_output(
            [
                "git",
                "-c",
                f"safe.directory={checkout.as_posix()}",
                "-C",
                str(checkout),
                "rev-parse",
                "HEAD",
            ],
            text=True,
        ).strip()
        folders = sorted((checkout / "raw" / "agent-reports").iterdir())
    count = 0
    for folder in folders:
        match = re.fullmatch(r"(.+)_(\d{4})(\d{2})(\d{2})(?:_\d+)?", folder.name)
        if not folder.is_dir() or not match or not (folder / "complete_report.md").is_file():
            continue
        symbol, year, month, day = match.groups()
        originals = {
            file.relative_to(folder).as_posix(): file.read_bytes()
            for file in sorted(folder.rglob("*.md"))
        }
        hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in originals.items()}
        identity_source = (
            str(folder) + json.dumps(hashes, sort_keys=True)
            if local else revision + "/" + folder.name
        )
        identity = hashlib.sha256(identity_source.encode()).hexdigest()[:32]
        try:
            store.get(identity)
            continue
        except KeyError:
            pass
        reports = {}
        capture = store.root / identity / "source"
        capture.mkdir(parents=True, exist_ok=True)
        for relative, raw in originals.items():
            target = capture / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)

        def read(relative, capture=capture):
            file = capture / relative
            return file.read_text(encoding="utf-8") if file.is_file() else ""

        for name in ("market", "fundamentals", "news", "sentiment"):
            reports[name + "_report"] = read(f"1_analysts/{name}.md")
        reports["investment_plan"] = read("2_research/manager.md")
        reports["investment_debate_state"] = {
            "bull_history": read("2_research/bull.md"),
            "bear_history": read("2_research/bear.md"),
        }
        reports["trader_investment_plan"] = read("3_trading/trader.md")
        reports["risk_debate_state"] = {
            name + "_history": read(f"4_risk/{name}.md")
            for name in ("aggressive", "conservative", "neutral")
        }
        reports["final_trade_decision"] = read("5_portfolio/decision.md")
        reports["original_report"] = read("complete_report.md")
        source = (
            str(folder / "complete_report.md") if local else
            f"https://github.com/Isaac-Lee/Alpha-Ledger/blob/{revision}/raw/agent-reports/{quote(folder.name)}/complete_report.md"
        )
        (capture / "provenance.json").write_text(
            json.dumps({"source": source, "revision": revision, "sha256": hashes}, indent=2),
            encoding="utf-8",
        )
        cfg = {
            "symbol": symbol,
            "date": f"{year}-{month}-{day}",
            "provider": "Local reports" if local else "Alpha-Ledger",
            "analysts": [
                n for n in ("market", "fundamentals", "news", "sentiment") if reports[n + "_report"]
            ],
            "depth": None,
            "quickModel": None,
            "deepModel": None,
        }
        store.save(
            {
                "id": identity,
                "config": cfg,
                "status": "imported",
                "stage": 5,
                "created": now(),
                "updated": now(),
                "reports": reports,
                "signal": extract_rating(reports["final_trade_decision"]) or "REVIEW",
                "error": None,
                "events": [],
                "source": source,
                "revision": revision,
            }
        )
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, nargs="?")
    parser.add_argument("--local", type=Path, nargs="+", help="Local SYMBOL_YYYYMMDD report folders")
    parser.add_argument("--data-dir", type=Path, default=Path(".web-data"))
    args = parser.parse_args()
    if (args.checkout is None) == (args.local is None):
        parser.error("Provide either an Alpha-Ledger checkout or --local report folders")
    store = JobStore(args.data_dir)
    try:
        print(f"Imported {import_reports(store, args.checkout, folders=args.local)} report sets.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
