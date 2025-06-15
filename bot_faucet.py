import requests
import time
import secrets
import threading
import logging
import json
import sys
from eth_account import Account
from web3 import Web3
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
from rich.table import Table

console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)
log = logging.getLogger("rich")

def load_config():
    """Memuat konfigurasi dari file config.json."""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
                
        console.print("[bold green]✔️ Konfigurasi dari config.json berhasil dimuat.[/]")
        return config
    except FileNotFoundError:
        console.print("[bold red]❌ Error: File 'config.json' tidak ditemukan. Harap buat file tersebut sesuai contoh.[/]")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print("[bold red]❌ Error: Format file 'config.json' tidak valid. Pastikan format JSON sudah benar.[/]")
        sys.exit(1)

config = load_config()

# Konfigurasi untuk kedua fitur
ANTI_CAPTCHA_KEY = config["ANTI_CAPTCHA_KEY"]

# Konfigurasi untuk fitur 2
ACCOUNTS = config.get("account", [])

TURNSTILE_SITEKEY = "0x4AAAAAABA4JXCaw9E2Py-9"
TURNSTILE_PAGE_URL = "https://testnet.megaeth.com/"
MEGAETH_API_URL = "https://carrot.megaeth.com/claim"
RPC_URL = "https://carrot.megaeth.com/rpc"
AMOUNT_TO_SEND_ETH = 0.00499

BASE_PROXY = {
    "http": config["PROXY"],
    "https": config["PROXY"]
}

def create_wallet():
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    return account.address, private_key

def submit_captcha(session, thread_id):
    params = {
        "clientKey": ANTI_CAPTCHA_KEY,
        "task": {
            "type": "TurnstileTaskProxyless",
            "websiteURL": TURNSTILE_PAGE_URL,
            "websiteKey": TURNSTILE_SITEKEY
        }
    }
    log.info(f"[Thread {thread_id}] [yellow]📤 Mengirim permintaan CAPTCHA ke Anti-Captcha...[/]")
    res = session.post("https://api.anti-captcha.com/createTask", json=params).json()
    if res.get("errorId") > 0:
        raise Exception(f"Gagal submit CAPTCHA: {res.get('errorDescription')}")
    log.info(f"[Thread {thread_id}] [green]✔️ Permintaan CAPTCHA diterima. Task ID: {res['taskId']}[/]")
    return res["taskId"]

def get_captcha_result(session, task_id, thread_id):
    with console.status(f"[bold yellow][Thread {thread_id}] ⏳ Menunggu hasil CAPTCHA...", spinner="dots") as status:
        for _ in range(20):
            time.sleep(3)
            params = {
                "clientKey": ANTI_CAPTCHA_KEY,
                "taskId": task_id
            }
            res = session.post("https://api.anti-captcha.com/getTaskResult", json=params).json()
            if res.get("errorId") > 0:
                raise Exception(f"Error CAPTCHA: {res.get('errorDescription')}")
            if res.get("status") == "ready":
                log.info(f"[Thread {thread_id}] [green]✅ CAPTCHA berhasil diselesaikan![/]")
                return res["solution"]["token"]
            elif res.get("status") != "processing":
                raise Exception(f"Error CAPTCHA: {res}")
        raise Exception("Timeout CAPTCHA.")

def claim(session, addr, token, thread_id):
    log.info(f"[Thread {thread_id}] [cyan]🚰 Mencoba melakukan klaim untuk wallet {addr[:10]}...[/]")
    headers = {
        "content-type": "text/plain;charset=UTF-8", "origin": "https://testnet.megaeth.com",
        "referer": "https://testnet.megaeth.com/", "user-agent": "Mozilla/5.0"
    }
    payload = {"addr": addr, "token": token}
    try:
        response = session.post(MEGAETH_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            log.info(f"[Thread {thread_id}] [bold green]🎉 Klaim sukses![/] Tx: [cyan]{data.get('txhash')}[/]")
            return True
        else:
            log.error(f"[Thread {thread_id}] [bold red]❌ Klaim gagal:[/] {data.get('message')}")
            return False
    except requests.exceptions.JSONDecodeError:
        log.error(f"[Thread {thread_id}] [bold red]❌ Gagal mem-parse response JSON. Status: {response.status_code}, Response: {response.text}[/]")
    except Exception as e:
        log.error(f"[Thread {thread_id}] [bold red]❌ Exception saat klaim: {e}[/]")
    return False

def send_eth(private_key, from_address, thread_id):
    log.info(f"[Thread {thread_id}] [cyan]💸 Mempersiapkan pengiriman ETH dari {from_address[:10]}...[/]")
    web3 = Web3(Web3.HTTPProvider(RPC_URL, {"proxies": BASE_PROXY}))
    if not web3.is_connected():
        log.error(f"[Thread {thread_id}] [red]❌ Gagal terhubung ke RPC {RPC_URL}[/]")
        return
        
    try:
        amount_wei = web3.to_wei(AMOUNT_TO_SEND_ETH, "ether")
        nonce = web3.eth.get_transaction_count(from_address)
        to_checksum = Web3.to_checksum_address(from_address)
        gas_price = web3.to_wei(0.01, "gwei")
        tx = {
            "from": from_address, "to": to_checksum, "value": amount_wei,
            "gas": 21000, "gasPrice": gas_price, "nonce": nonce, "chainId": 6342
        }
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        log.info(f"[Thread {thread_id}] [bold green]🚀 ETH berhasil dikirim![/] Tx hash: [cyan]{web3.to_hex(tx_hash)}[/]")
    except Exception as e:
        log.error(f"[Thread {thread_id}] [bold red]❌ Gagal mengirim ETH: {e}[/]")

def check_balance(address, thread_id):
    web3 = Web3(Web3.HTTPProvider(RPC_URL, {"proxies": BASE_PROXY}))
    if not web3.is_connected():
        log.error(f"[Thread {thread_id}] [red]❌ Gagal terhubung ke RPC untuk cek saldo.[/]")
        return 0
    balance_wei = web3.eth.get_balance(address)
    balance_eth = web3.from_wei(balance_wei, 'ether')
    log.info(f"[Thread {thread_id}] 💰 Saldo [yellow]{address[:10]}[/]: [bold green]{balance_eth:.4f} ETH[/]")
    return balance_eth
    
def process_fitur_2_looping(private_key, proxy, thread_id, stop_event):
    account = Account.from_key(private_key)
    address = account.address
    log.info(f"[Thread {thread_id}] [bold blue]Memulai loop untuk wallet {address[:10]}...[/]")
    
    while not stop_event.is_set():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.info(f"\n[Thread {thread_id}] [magenta]({now_str})[/] Memulai siklus untuk [yellow]{address[:10]}[/]")
        session = requests.Session()
        session.proxies.update({
            "http": proxy,
            "https": proxy
        })
        
        try:
            check_balance(address, thread_id)
            cap_id = submit_captcha(session, thread_id)
            cap_token = get_captcha_result(session, cap_id, thread_id)
            claim(session, address, cap_token, thread_id)
        except Exception as e:
            log.error(f"[Thread {thread_id}] [red]❗ Error pada wallet {address[:10]}: {e}[/]")
        finally:
            session.close()

        next_run = datetime.now() + timedelta(days=1)
        wait_seconds = 86400
        log.info(f"[Thread {thread_id}] [blue]⏰ Siklus selesai. Klaim berikutnya pada: {next_run.strftime('%Y-%m-%d %H:%M:%S')}[/]")

        with console.status(f"[bold cyan][Thread {thread_id}] Menunggu {wait_seconds // 3600} jam...", spinner="earth") as status:
            for i in range(wait_seconds):
                if stop_event.is_set(): break
                if i % 60 == 0:
                    remaining_seconds = wait_seconds - i
                    hours, remainder = divmod(remaining_seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    status.update(f"[bold cyan][Thread {thread_id}] Menunggu... [green]{hours} jam {minutes} menit lagi[/]")
                time.sleep(1)

def run_fitur_2_allkeys(stop_event):
    if not ACCOUNTS:
        log.error("❌ Tidak ada wallet yang ditemukan di config.json. Keluar dari Fitur 2.")
        return

    threads = []
    for i, account in enumerate(ACCOUNTS):
        t = threading.Thread(target=process_fitur_2_looping, args=(account["private_key"], account["proxy"], i + 1, stop_event))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

def main():
    title = Panel(
        Text("MEGAETH FAUCET BOT", justify="center", style="bold magenta"),
        title="[bold green]By: Bény G.[/]",
        subtitle="[cyan]v2.1 with Config File[/]"
    )
    console.print(title)

    menu_table = Table(show_header=False, box=None)
    menu_table.add_row("[bold cyan]1.[/]", "Load dari config.json (klaim tiap 24 jam)")
    console.print(Panel(menu_table, title="[yellow]PILIH FITUR[/]", border_style="yellow"))

    mode = console.input("[bold green]Pilih fitur (1): [/]").strip()
    stop_event = threading.Event()

    try:
        if mode == "1":
            run_fitur_2_allkeys(stop_event)
        else:
            log.error("❌ Input tidak valid. Harap pilih 1.")
    except (KeyboardInterrupt, EOFError):
        log.warning("\n[bold yellow]⚠️ Program dihentikan oleh pengguna. Mengirim sinyal berhenti ke semua thread...[/]")
        stop_event.set()
        log.info("[bold red]🛑 Program telah dihentikan.[/]")
    except ValueError:
        log.error("❌ Input thread tidak valid. Harap masukkan angka.")

if __name__ == "__main__":
    main()