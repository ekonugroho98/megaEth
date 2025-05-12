import os
from rich.console import Console
from rich.text import Text
from tabulate import tabulate
from rich.table import Table
from rich import box
from rich.panel import Panel


def show_logo():
    """Отображает стильный логотип STARLABS"""
    # Очищаем экран
    os.system("cls" if os.name == "nt" else "clear")

    console = Console()

    logo = """
    ╔═════════════════════════════════════════════════════════════════════════╗
    ║                                                                         ║
    ║                                ███████╗██╗  ██╗ ██████╗                 ║
    ║                                ██╔════╝██║ ██╔╝██╔═══██╗                ║
    ║                                ███████╗█████╔╝ ██║   ██║                ║
    ║                                ██║     ██╔═██╗ ██║   ██║                ║
    ║                                ███████║██║  ██╗╚██████╔╝                ║
    ║                                ╚══════╝╚═╝  ╚═╝ ╚═════╝                 ║
    ║                                                                         ║
    ╚═════════════════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(logo, style="bold blue"))


def show_dev_info():
    """Displays development and version information"""
    console = Console()

    info = """
    [bold green]JPEKO MegaETH Bot[/bold green]
    [yellow]Version:[/yellow] 1.0.0
    [yellow]Developer:[/yellow] JPEKO Team
    [yellow]Description:[/yellow] Advanced ETH Trading Bot
    """
    console.print(Panel(info, style="bold white"))
