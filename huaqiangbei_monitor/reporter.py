"""终端报表展示（基于 Rich）"""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.rule import Rule

console = Console()


def _price_color(change_pct: Optional[float]) -> str:
    if change_pct is None:
        return "white"
    if change_pct > 0:
        return "bright_red"
    if change_pct < 0:
        return "bright_green"
    return "white"


def print_latest_prices(part_number: str, rows: list):
    """打印某型号最新价格表"""
    table = Table(
        title=f"[bold cyan]{part_number}[/bold cyan] 最新报价",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        expand=False,
    )
    table.add_column("来源", style="cyan", min_width=16)
    table.add_column("单价(¥)", justify="right", style="yellow", min_width=10)
    table.add_column("起购量", justify="right", min_width=8)
    table.add_column("库存", justify="right", min_width=10)
    table.add_column("供应商", min_width=14)
    table.add_column("抓取时间", min_width=16)

    for row in rows:
        table.add_row(
            str(row.source_name or row.source),
            f"{row.price:.4f}",
            str(row.min_qty or 1),
            str(row.stock_qty or "-"),
            str(row.supplier or "-"),
            row.scraped_at.strftime("%m-%d %H:%M") if row.scraped_at else "-",
        )

    if not rows:
        table.add_row("[dim]暂无数据[/dim]", "", "", "", "", "")

    console.print(table)


def print_price_history(part_number: str, rows: list, source: Optional[str] = None):
    """打印价格历史"""
    title = f"{part_number} 价格历史"
    if source:
        title += f" [{source}]"

    table = Table(title=title, box=box.SIMPLE, header_style="bold blue", expand=False)
    table.add_column("来源", style="cyan", min_width=16)
    table.add_column("单价(¥)", justify="right", style="yellow", min_width=10)
    table.add_column("起购量", justify="right", min_width=8)
    table.add_column("库存", justify="right", min_width=10)
    table.add_column("时间", min_width=16)

    for row in rows:
        table.add_row(
            str(row.source_name or row.source),
            f"{row.price:.4f}",
            str(row.min_qty or 1),
            str(row.stock_qty or "-"),
            row.scraped_at.strftime("%Y-%m-%d %H:%M") if row.scraped_at else "-",
        )

    console.print(table)


def print_alerts(alerts: list):
    """打印价格告警"""
    if not alerts:
        console.print("[dim]最近无价格告警[/dim]")
        return

    table = Table(
        title="[bold red]价格变化告警[/bold red]",
        box=box.HEAVY_HEAD,
        header_style="bold red",
        expand=False,
    )
    table.add_column("型号", style="cyan", min_width=18)
    table.add_column("来源", min_width=14)
    table.add_column("旧价(¥)", justify="right", min_width=10)
    table.add_column("新价(¥)", justify="right", min_width=10)
    table.add_column("变化幅度", justify="right", min_width=10)
    table.add_column("时间", min_width=16)

    for alert in alerts:
        color = "bright_red" if alert.direction == "up" else "bright_green"
        arrow = "↑" if alert.direction == "up" else "↓"
        table.add_row(
            alert.part_number,
            alert.source,
            f"{alert.old_price:.4f}",
            f"[{color}]{alert.new_price:.4f}[/{color}]",
            f"[{color}]{arrow} {abs(alert.change_pct):.1f}%[/{color}]",
            alert.alerted_at.strftime("%m-%d %H:%M") if alert.alerted_at else "-",
        )

    console.print(table)


def print_components(components: list):
    """打印监控的元器件列表"""
    table = Table(
        title="监控元器件列表",
        box=box.ROUNDED,
        header_style="bold green",
        expand=False,
    )
    table.add_column("#", justify="right", style="dim", min_width=4)
    table.add_column("型号", style="cyan bold", min_width=20)
    table.add_column("描述", min_width=30)
    table.add_column("分类", min_width=12)
    table.add_column("状态", min_width=8)

    for i, comp in enumerate(components, 1):
        status = "[green]启用[/green]" if comp.is_active else "[red]停用[/red]"
        table.add_row(
            str(i),
            comp.part_number,
            comp.description or "-",
            comp.category or "-",
            status,
        )

    console.print(table)


def print_stats(stats: dict):
    """打印系统统计信息"""
    text = (
        f"[cyan]监控型号[/cyan]: {stats.get('total_components', 0)}  "
        f"[yellow]价格记录[/yellow]: {stats.get('total_records', 0)}  "
        f"[red]告警总数[/red]: {stats.get('total_alerts', 0)}  "
        f"[bright_red]未读告警[/bright_red]: {stats.get('unread_alerts', 0)}"
    )
    console.print(Panel(text, title="系统统计", border_style="blue"))


def print_banner():
    banner = """
[bold cyan]
 ██╗  ██╗██╗   ██╗ █████╗  ██████╗ ██╗ █████╗ ███╗   ██╗ ██████╗ ██████╗ ███████╗██╗
 ██║  ██║██║   ██║██╔══██╗██╔═══██╗██║██╔══██╗████╗  ██║██╔══██╗██╔══██╗██╔════╝██║
 ███████║██║   ██║███████║██║   ██║██║███████║██╔██╗ ██║██████╔╝██████╔╝█████╗  ██║
 ██╔══██║██║   ██║██╔══██║██║▄▄ ██║██║██╔══██║██║╚██╗██║██╔══██╗██╔══██╗██╔══╝  ██║
 ██║  ██║╚██████╔╝██║  ██║╚██████╔╝██║██║  ██║██║ ╚████║██████╔╝██████╔╝███████╗██║
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚══▀▀═╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═════╝ ╚══════╝╚═╝
[/bold cyan]"""
    console.print(banner)
    console.print(
        Panel(
            "[bold]华强北元器件价格监控系统[/bold]  |  "
            "[dim]支持: 立创商城 · 华强北网 · Allchips · 云汉芯城[/dim]",
            border_style="cyan",
        )
    )
