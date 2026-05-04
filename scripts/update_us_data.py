#!/usr/bin/env python3
"""
Update US Stock Data for Qlib
==============================
Wraps Qlib's Yahoo Collector to incrementally update US stock data.

Usage:
  # Update data to today
  python scripts/update_us_data.py

  # Update to a specific date
  python scripts/update_us_data.py --end-date 2026-05-02

  # Update and rebuild concept matrix
  python scripts/update_us_data.py --rebuild-concept

  # Dry run (show plan only)
  python scripts/update_us_data.py --dry-run

  # Fast mode: 4 workers + 2 retries (default)
  python scripts/update_us_data.py --end-date 2026-05-02 --max-workers 4 --retry 2
"""
import os
import sys
import types
import pickle
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QLIB_SCRIPTS = Path.home() / "WorkSpace" / "QoderWorkspace" / "qlib" / "scripts"

# Monkey-patch: qlib 0.9.7 lacks qlib.utils.pickle_utils which the collector needs
if "qlib.utils.pickle_utils" not in sys.modules:
    _dummy = types.ModuleType("qlib.utils.pickle_utils")
    _dummy.restricted_pickle_load = pickle.load
    sys.modules["qlib.utils.pickle_utils"] = _dummy

# Default Qlib data directory
DEFAULT_QLIB_DIR = os.path.expanduser("~/.qlib/qlib_data/us_data")


def get_calendar_range(qlib_dir):
    """Read the first and last dates from the calendar file."""
    cal_path = Path(qlib_dir) / "calendars" / "day.txt"
    if not cal_path.exists():
        return None, None
    with open(cal_path, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        return None, None
    return lines[0], lines[-1]


def count_trading_days(qlib_dir):
    """Count trading days in calendar."""
    cal_path = Path(qlib_dir) / "calendars" / "day.txt"
    if not cal_path.exists():
        return 0
    with open(cal_path, "r") as f:
        return sum(1 for l in f if l.strip())


def update_data(qlib_dir, end_date, delay, max_workers=4, retry=2, dry_run=False):
    """Run the Qlib Yahoo Collector update_data_to_bin via Python API."""
    collector_dir = str(QLIB_SCRIPTS)

    if not Path(collector_dir).exists():
        print(f"ERROR: Cannot find qlib scripts at {collector_dir}")
        print(f"  Please ensure the qlib repo is cloned at ~/WorkSpace/QoderWorkspace/qlib/")
        return False

    if dry_run:
        print(f"[DRY RUN] Would call:")
        print(f"  Run(region='US', interval='1d', max_workers={max_workers}).update_data_to_bin(")
        print(f"      qlib_data_1d_dir='{qlib_dir}',")
        print(f"      end_date='{end_date}',")
        print(f"      delay={delay})")
        print(f"  Collector retry={retry}")
        return True

    # Add collector paths to sys.path (BaseRun needs all of these)
    paths_to_add = [
        collector_dir,                                              # scripts/
        str(Path(collector_dir) / "data_collector"),               # scripts/data_collector/
        str(Path(collector_dir) / "data_collector" / "yahoo"),     # scripts/data_collector/yahoo/ (for "import collector")
    ]
    for p in paths_to_add:
        if p not in sys.path:
            sys.path.insert(0, p)

    print(f"Running Qlib Yahoo Collector...")
    print(f"  Target:      {qlib_dir}")
    print(f"  End date:    {end_date}")
    print(f"  Delay:       {delay}s")
    print(f"  Workers:     {max_workers}")
    print(f"  Retry:       {retry} (Yahoo default: 5)")
    print()

    try:
        from data_collector.yahoo.collector import Run, YahooCollector
        from data_collector.base import BaseCollector

        # Monkey-patch 1: reduce retry count to speed up delisted stock handling
        # IMPORTANT: BaseRun uses importlib.import_module("collector") which creates
        # a separate module object from "data_collector.yahoo.collector". Must patch BOTH.
        import importlib
        _collector_mod = importlib.import_module("collector")
        _collector_mod.YahooCollector.retry = retry
        YahooCollector.retry = retry
        print(f"  [patch] YahooCollector.retry = {retry} (both module refs)")

        # Monkey-patch 2: use threads instead of processes for parallel download
        # joblib default (loky) uses multiprocessing which fails on non-picklable
        # collector instances. Threads work fine for I/O-bound HTTP downloads.
        if max_workers > 1:
            _orig_collector = BaseCollector._collector

            def _threaded_collector(self, instrument_list):
                from joblib import Parallel, delayed
                from tqdm import tqdm
                error_symbol = []
                res = Parallel(n_jobs=self.max_workers, prefer="threads")(
                    delayed(self._simple_collector)(_inst) for _inst in tqdm(instrument_list)
                )
                for _symbol, _result in zip(instrument_list, res):
                    if _result != self.NORMAL_FLAG:
                        error_symbol.append(_symbol)
                print(error_symbol)
                import logging
                logging.getLogger("qlib").info(f"error symbol nums: {len(error_symbol)}")
                logging.getLogger("qlib").info(f"current get symbol nums: {len(instrument_list)}")
                error_symbol.extend(self.mini_symbol_map.keys())
                return sorted(set(error_symbol))

            BaseCollector._collector = _threaded_collector
            print(f"  [patch] BaseCollector._collector → threads (n_jobs={max_workers})")

        runner = Run(
            source_dir=str(Path(collector_dir) / "source"),
            normalize_dir=str(Path(collector_dir) / "normalize"),
            max_workers=max_workers,
            interval="1d",
            region="US",
        )
        runner.update_data_to_bin(
            qlib_data_1d_dir=qlib_dir,
            end_date=end_date,
            delay=delay,
        )
        return True
    except Exception as e:
        print(f"\nERROR during data update: {e}")
        import traceback
        traceback.print_exc()
        return False


def rebuild_concept(market="sp500"):
    """Rebuild stock2concept matrix by running build_us_concept_data.py."""
    script_path = PROJECT_ROOT / "scripts" / "build_us_concept_data.py"
    if not script_path.exists():
        print(f"WARNING: {script_path} not found, skipping concept rebuild")
        return False

    print(f"\nRebuilding stock2concept matrix for {market}...")
    result = subprocess.run(
        [sys.executable, str(script_path), "--market", market, "--skip-yfinance"],
        capture_output=False,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Update US stock data for Qlib")
    parser.add_argument("--end-date", type=str, default=None,
                        help="End date for data update (open interval). Default: tomorrow")
    parser.add_argument("--qlib-dir", type=str, default=DEFAULT_QLIB_DIR,
                        help=f"Qlib US data directory (default: {DEFAULT_QLIB_DIR})")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between Yahoo API calls in seconds (default: 1.0)")
    parser.add_argument("--rebuild-concept", action="store_true",
                        help="Rebuild stock2concept matrix after data update")
    parser.add_argument("--market", type=str, default="sp500",
                        help="Market for concept rebuild (default: sp500)")
    parser.add_argument("--max-workers", type=int, default=4,
                        help="Download concurrency (default: 4, Yahoo default was 1)")
    parser.add_argument("--retry", type=int, default=2,
                        help="Retry count per stock on failure (default: 2, Yahoo default was 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without executing")
    args = parser.parse_args()

    # Determine end date
    if args.end_date:
        end_date = args.end_date
    else:
        end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    qlib_dir = os.path.expanduser(args.qlib_dir)

    # Show current state
    first_date, last_date = get_calendar_range(qlib_dir)
    n_days = count_trading_days(qlib_dir)

    print("=" * 60)
    print("  US Stock Data Update")
    print("=" * 60)

    if first_date and last_date:
        print(f"  Current data:  {first_date} ~ {last_date}")
        print(f"  Trading days:  {n_days}")
        print(f"  Update to:     {end_date}")
    else:
        print(f"  No existing data found in {qlib_dir}")
        print(f"  Update to:     {end_date}")
    print("=" * 60)
    print()

    if args.dry_run:
        print("[DRY RUN MODE] No changes will be made.\n")

    # Run update
    success = update_data(qlib_dir, end_date, args.delay,
                          max_workers=args.max_workers, retry=args.retry,
                          dry_run=args.dry_run)

    if not success and not args.dry_run:
        print("\nERROR: Data update failed. Check the error messages above.")
        sys.exit(1)

    if not args.dry_run:
        # Verify update
        new_first, new_last = get_calendar_range(qlib_dir)
        new_n_days = count_trading_days(qlib_dir)

        print()
        print("=" * 60)
        print("  Update Complete")
        print("=" * 60)
        print(f"  Data range:    {new_first} ~ {new_last}")
        print(f"  Trading days:  {new_n_days} (was {n_days}, +{new_n_days - n_days})")
        print("=" * 60)

    # Rebuild concept matrix if requested
    if args.rebuild_concept:
        if args.dry_run:
            print("\n[DRY RUN] Would rebuild stock2concept matrix")
        else:
            rebuild_concept(args.market)


if __name__ == "__main__":
    main()
