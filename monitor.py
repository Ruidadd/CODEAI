#!/usr/bin/env python3
"""
CLI entry point for the realtime alternative data monitor.

Usage:
  python monitor.py run              # start continuous monitoring (Ctrl+C to stop)
  python monitor.py once             # single poll, store results, exit
  python monitor.py status           # print latest snapshot table
  python monitor.py alerts [--hours N]  # show recent alerts

Options:
  --db PATH         SQLite database path (default: monitor_data.db)
  --webhook URL     POST alerts to this webhook URL
  --no-alerts       suppress console alert panels
"""
import argparse
import logging
import sys

from rich.console import Console

from realtime_monitor import storage
from realtime_monitor.config import AlertConfig
from realtime_monitor.scheduler import Monitor, _make_status_table

console = Console()


def cmd_run(args: argparse.Namespace) -> None:
    cfg = AlertConfig(
        webhook_url=args.webhook,
        log_to_console=not args.no_alerts,
    )
    Monitor(db_path=args.db, cfg=cfg).run()


def cmd_once(args: argparse.Namespace) -> None:
    cfg = AlertConfig(
        webhook_url=args.webhook,
        log_to_console=not args.no_alerts,
    )
    Monitor(db_path=args.db, cfg=cfg, once=True).run()
    console.print("[green]Single poll complete.[/]")


def cmd_status(args: argparse.Namespace) -> None:
    storage.init_db(args.db)
    console.print(_make_status_table(args.db))


def cmd_alerts(args: argparse.Namespace) -> None:
    from tabulate import tabulate
    storage.init_db(args.db)
    rows = storage.get_recent_alerts(hours=args.hours, db_path=args.db)
    if not rows:
        console.print("[dim]No alerts in the last %d hours.[/]" % args.hours)
        return
    data = [(r["ts"][:19], r["severity"], r["category"], r["message"]) for r in rows]
    console.print(tabulate(data, headers=["Timestamp", "Severity", "Category", "Message"],
                           tablefmt="rounded_outline"))


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Realtime alternative data monitor")
    parser.add_argument("--db", default="monitor_data.db", help="SQLite DB path")
    parser.add_argument("--webhook", default="", help="Webhook URL for alerts")
    parser.add_argument("--no-alerts", action="store_true", help="Suppress console alert panels")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run", help="Continuous monitoring")
    sub.add_parser("once", help="Single poll then exit")
    sub.add_parser("status", help="Print latest snapshot")
    alerts_p = sub.add_parser("alerts", help="Show recent alerts")
    alerts_p.add_argument("--hours", type=int, default=24)

    args = parser.parse_args()

    dispatch = {
        "run": cmd_run,
        "once": cmd_once,
        "status": cmd_status,
        "alerts": cmd_alerts,
    }

    if args.command not in dispatch:
        parser.print_help()
        sys.exit(1)

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
