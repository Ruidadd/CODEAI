"""命令行界面"""

import logging
import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from .monitor import PriceMonitor
from .reporter import (
    console,
    print_banner,
    print_components,
    print_latest_prices,
    print_price_history,
    print_alerts,
    print_stats,
)
from .config import DEFAULT_COMPONENTS, DEFAULT_INTERVAL_MINUTES, PRICE_CHANGE_ALERT_THRESHOLD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _get_monitor(db: str) -> PriceMonitor:
    from .config import DB_PATH
    return PriceMonitor(db_path=db if db else None)


@click.group()
@click.option("--db", default=None, help="数据库路径（默认 price_monitor.db）")
@click.pass_context
def cli(ctx, db):
    """华强北元器件价格监控系统"""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


@cli.command("init")
@click.option("--with-defaults", is_flag=True, default=True, help="导入默认元器件列表")
@click.pass_context
def cmd_init(ctx, with_defaults):
    """初始化数据库并导入默认元器件"""
    print_banner()
    monitor = _get_monitor(ctx.obj["db"])
    if with_defaults:
        for part in DEFAULT_COMPONENTS:
            monitor.add_component(part)
        console.print(f"[green]✓[/green] 已导入 {len(DEFAULT_COMPONENTS)} 个默认元器件")
    console.print("[green]✓[/green] 数据库初始化完成")


@cli.command("add")
@click.argument("part_number")
@click.option("--desc", default="", help="描述")
@click.option("--category", default="", help="分类")
@click.pass_context
def cmd_add(ctx, part_number, desc, category):
    """添加监控的元器件型号"""
    monitor = _get_monitor(ctx.obj["db"])
    monitor.add_component(part_number.upper(), desc, category)
    console.print(f"[green]✓[/green] 已添加 [cyan]{part_number.upper()}[/cyan] 到监控列表")


@cli.command("remove")
@click.argument("part_number")
@click.pass_context
def cmd_remove(ctx, part_number):
    """停止监控某元器件"""
    monitor = _get_monitor(ctx.obj["db"])
    monitor.remove_component(part_number.upper())
    console.print(f"[yellow]已停止监控[/yellow] [cyan]{part_number.upper()}[/cyan]")


@cli.command("list")
@click.pass_context
def cmd_list(ctx):
    """列出所有监控的元器件"""
    monitor = _get_monitor(ctx.obj["db"])
    components = monitor.list_components()
    print_components(components)
    print_stats(monitor.get_stats())


@cli.command("fetch")
@click.argument("parts", nargs=-1)
@click.option("--all", "fetch_all", is_flag=True, help="抓取所有已监控型号")
@click.pass_context
def cmd_fetch(ctx, parts, fetch_all):
    """立即抓取一次价格

    示例:\n
      monitor fetch STM32F103C8T6\n
      monitor fetch --all
    """
    monitor = _get_monitor(ctx.obj["db"])

    if fetch_all:
        part_numbers = None  # run_once 里会读取数据库
    elif parts:
        part_numbers = [p.upper() for p in parts]
        for p in part_numbers:
            monitor.add_component(p)
    else:
        console.print("[red]请指定型号或使用 --all[/red]")
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("正在抓取价格...", total=None)
        stats = monitor.run_once(part_numbers)
        progress.update(task, completed=True)

    console.print(
        f"[green]✓[/green] 抓取完成 — "
        f"获取 [cyan]{stats['fetched']}[/cyan] 条, "
        f"保存 [cyan]{stats['saved']}[/cyan] 条, "
        f"告警 [red]{stats['alerts']}[/red] 条"
    )


@cli.command("price")
@click.argument("part_number")
@click.pass_context
def cmd_price(ctx, part_number):
    """查看某型号的最新价格"""
    monitor = _get_monitor(ctx.obj["db"])
    rows = monitor.get_latest_prices(part_number.upper())
    print_latest_prices(part_number.upper(), rows)


@cli.command("history")
@click.argument("part_number")
@click.option("--source", default=None, help="只看某个数据源")
@click.option("--days", default=30, show_default=True, help="查看最近N天")
@click.pass_context
def cmd_history(ctx, part_number, source, days):
    """查看价格历史记录"""
    monitor = _get_monitor(ctx.obj["db"])
    rows = monitor.get_price_history(part_number.upper(), source=source, days=days)
    print_price_history(part_number.upper(), rows, source)


@cli.command("alerts")
@click.option("--hours", default=24, show_default=True, help="查看最近N小时的告警")
@click.pass_context
def cmd_alerts(ctx, hours):
    """查看价格变化告警"""
    monitor = _get_monitor(ctx.obj["db"])
    alerts = monitor.get_recent_alerts(hours=hours)
    print_alerts(alerts)


@cli.command("watch")
@click.option("--interval", default=DEFAULT_INTERVAL_MINUTES, show_default=True, help="监控间隔（分钟）")
@click.argument("parts", nargs=-1)
@click.pass_context
def cmd_watch(ctx, interval, parts):
    """启动定时监控（持续运行）

    示例:\n
      monitor watch                  # 监控所有已注册型号\n
      monitor watch STM32F103C8T6    # 只监控指定型号\n
      monitor watch --interval 30    # 每30分钟抓取一次
    """
    print_banner()
    monitor = _get_monitor(ctx.obj["db"])

    part_numbers = [p.upper() for p in parts] if parts else None
    if part_numbers:
        for p in part_numbers:
            monitor.add_component(p)

    console.print(
        f"[cyan]启动监控[/cyan] — 间隔 [bold]{interval}[/bold] 分钟  "
        f"告警阈值 [bold]{PRICE_CHANGE_ALERT_THRESHOLD}%[/bold]  "
        f"按 [bold]Ctrl+C[/bold] 退出"
    )
    try:
        monitor.run_scheduler(part_numbers=part_numbers, interval_minutes=interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]监控已停止[/yellow]")


@cli.command("web")
@click.option("--host", default="0.0.0.0", show_default=True, help="监听地址")
@click.option("--port", default=8000, show_default=True, help="端口")
@click.option("--fetch-interval", default=30, show_default=True,
              help="后台自动抓取间隔(分钟), 0 表示不自动抓取")
@click.pass_context
def cmd_web(ctx, host, port, fetch_interval):
    """启动 Web 实时监控面板

    示例:\n
      monitor web                       # http://localhost:8000\n
      monitor web --fetch-interval 15   # 每15分钟后台自动抓取\n
      monitor web --fetch-interval 0    # 仅展示, 不自动抓取
    """
    from .webapp import run_server

    print_banner()
    console.print(
        f"[cyan]Web 面板启动[/cyan] — http://localhost:{port}  "
        f"后台抓取间隔 [bold]{fetch_interval}[/bold] 分钟  按 [bold]Ctrl+C[/bold] 退出"
    )
    run_server(host, port, ctx.obj["db"], fetch_interval)


@cli.command("export")
@click.argument("part_number")
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv")
@click.option("--output", "-o", default=None, help="输出文件路径")
@click.option("--days", default=30, show_default=True)
@click.pass_context
def cmd_export(ctx, part_number, fmt, output, days):
    """导出价格数据"""
    import json
    import csv
    import io

    monitor = _get_monitor(ctx.obj["db"])
    rows = monitor.get_price_history(part_number.upper(), days=days)

    data = [
        {
            "part_number": r.part_number,
            "source": r.source_name or r.source,
            "price": r.price,
            "currency": r.currency,
            "min_qty": r.min_qty,
            "stock_qty": r.stock_qty,
            "supplier": r.supplier,
            "scraped_at": r.scraped_at.isoformat() if r.scraped_at else "",
        }
        for r in rows
    ]

    if not output:
        output = f"{part_number.upper()}_prices.{fmt}"

    if fmt == "json":
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        with open(output, "w", newline="", encoding="utf-8-sig") as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    console.print(f"[green]✓[/green] 已导出 {len(data)} 条记录到 [cyan]{output}[/cyan]")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
