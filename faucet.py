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
    required_keys = ["APIKEY", "TO_ADDRESS", "PROXY_HOST", "PROXY_PORT", "PROXY_USER", "PROXY_PASS"]
    try:
        with open("config.json", "r") as f:
            config = json.load(f)

        for key in required_keys:
            if key not in config:
                log.critical(f"[bold red]❌ Error: Key '{key}' tidak ditemukan di config.json. Harap lengkapi file konfigurasi.[/]")
                sys.exit(1) 
                
        log.info("[bold green]✔️ Konfigurasi dari config.json berhasil dimuat.[/]")
        return config
    except FileNotFoundError:
        log.critical("[bold red]❌ Error: File 'config.json' tidak ditemukan. Harap buat file tersebut sesuai contoh.[/]")
        sys.exit(1)
    except json.JSONDecodeError:
        log.critical("[bold red]❌ Error: Format file 'config.json' tidak valid. Pastikan format JSON sudah benar.[/]")
        sys.exit(1)

config = load_config()

APIKEY = config["APIKEY"]
TO_ADDRESS = config["TO_ADDRESS"]
PROXY_HOST = config["PROXY_HOST"]
PROXY_PORT = config["PROXY_PORT"]
PROXY_USER = config["PROXY_USER"]
PROXY_PASS = config["PROXY_PASS"]

TURNSTILE_SITEKEY = "0x4AAAAAABA4JXCaw9E2Py-9"
TURNSTILE_PAGE_URL = "https://testnet.megaeth.com/"
MEGAETH_API_URL = "https://carrot.megaeth.com/claim"
RPC_URL = "https://carrot.megaeth.com/rpc"
AMOUNT_TO_SEND_ETH = 0.00499

BASE_PROXY = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
}


def load_keys(filename="key.txt"):
    try:
        with open(filename, "r") as f:
            keys = [line.strip() for line in f if line.strip()]
            log.info(f"[green]🔑 Berhasil memuat {len(keys)} kunci dari {filename}[/]")
            return keys
    except FileNotFoundError:
        log.warning(f"[yellow]⚠️ File '{filename}' tidak ditemukan.[/]")
        return []

def create_wallet():
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    return account.address, private_key

def submit_captcha(session, thread_id):
    params = {
        "key": APIKEY, "method": "turnstile", "sitekey": TURNSTILE_SITEKEY,
        "pageurl": TURNSTILE_PAGE_URL, "json": "1"
    }
    log.info(f"[Thread {thread_id}] [yellow]📤 Mengirim permintaan CAPTCHA...[/]")
    res = session.post("http://api.multibot.in/in.php", files={k: (None, v) for k, v in params.items()}).json()
    if res["status"] != 1:
        raise Exception(f"Gagal submit CAPTCHA: {res}")
    log.info(f"[Thread {thread_id}] [green]✔️ Permintaan CAPTCHA diterima. ID: {res['request']}[/]")
    return res["request"]

def get_captcha_result(session, captcha_id, thread_id):
    with console.status(f"[bold yellow][Thread {thread_id}] ⏳ Menunggu hasil CAPTCHA...", spinner="dots") as status:
        for _ in range(20):
            time.sleep(3)
            res = session.get("http://api.multibot.in/res.php", params={
                "key": APIKEY, "action": "get", "id": captcha_id, "json": "1"
            }).json()
            if res["status"] == 1:
                log.info(f"[Thread {thread_id}] [green]✅ CAPTCHA berhasil diselesaikan![/]")
                return res["request"]
            elif res["request"] != "CAPCHA_NOT_READY":
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
        to_checksum = Web3.to_checksum_address(TO_ADDRESS)
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
    
def process_fitur_1(thread_id, stop_event):
    if stop_event.is_set(): return
    log.info(f"[bold blue]-- Memulai Proses di Thread {thread_id} --[/]")
    session = requests.Session()
    session.proxies.update(BASE_PROXY)
    address, private_key = create_wallet()

    wallet_info = Text(f"Address: {address}\nPrivate Key: {private_key[:30]}...", justify="left")
    console.print(Panel(wallet_info, title=f"🔐 [Thread {thread_id}] Wallet Baru Dibuat", border_style="green", title_align="left"))
    
    try:
        cap_id = submit_captcha(session, thread_id)
        cap_token = get_captcha_result(session, cap_id, thread_id)
        if claim(session, address, cap_token, thread_id):
            time.sleep(10) 
            send_eth(private_key, address, thread_id)
    except Exception as e:
        log.error(f"[Thread {thread_id}] [red]❗ Error pada proses utama: {e}[/]")
    finally:
        session.close()
        log.info(f"[bold blue]-- Proses Selesai di Thread {thread_id} --[/]\n")

def run_fitur_1_multithread(num_threads, stop_event):
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=process_fitur_1, args=(i + 1, stop_event))
        threads.append(t)
        t.start()
        time.sleep(0.1)
    for t in threads:
        t.join()

def process_fitur_2_looping(private_key, thread_id, stop_event):
    account = Account.from_key(private_key)
    address = account.address
    log.info(f"[Thread {thread_id}] [bold blue]Memulai loop untuk wallet {address[:10]}...[/]")
    
    while not stop_event.is_set():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.info(f"\n[Thread {thread_id}] [magenta]({now_str})[/] Memulai siklus untuk [yellow]{address[:10]}[/]")
        session = requests.Session()
        session.proxies.update(BASE_PROXY)
        
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
    keys = load_keys()
    if not keys:
        log.error("❌ File key.txt kosong atau tidak ditemukan. Keluar dari Fitur 2.")
        return

    threads = []
    for i, key in enumerate(keys):
        t = threading.Thread(target=process_fitur_2_looping, args=(key, i + 1, stop_event))
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
    menu_table.add_row("[bold cyan]1.[/]", "Auto Create Wallet & Claim (looping)")
    menu_table.add_row("[bold cyan]2.[/]", "Load dari key.txt (klaim tiap 24 jam)")
    console.print(Panel(menu_table, title="[yellow]PILIH FITUR[/]", border_style="yellow"))

    mode = console.input("[bold green]Pilih fitur (1/2): [/]").strip()
    stop_event = threading.Event()

    try:
        if mode == "1":
            num_threads_str = console.input("[bold green]Jumlah thread yang ingin dijalankan bersamaan: [/]").strip()
            num_threads = int(num_threads_str)
            while not stop_event.is_set():
                run_fitur_1_multithread(num_threads, stop_event)
                log.info("[bold yellow]🌀 Semua thread telah selesai. Menunggu 5 detik sebelum memulai loop berikutnya...[/]")
                time.sleep(5)
        elif mode == "2":
            run_fitur_2_allkeys(stop_event)
        else:
            log.error("❌ Input tidak valid. Harap pilih 1 atau 2.")
    except (KeyboardInterrupt, EOFError):
        log.warning("\n[bold yellow]⚠️ Program dihentikan oleh pengguna. Mengirim sinyal berhenti ke semua thread...[/]")
        stop_event.set()
        log.info("[bold red]🛑 Program telah dihentikan.[/]")
    except ValueError:
        log.error("❌ Input thread tidak valid. Harap masukkan angka.")

if __name__ == "__main__":
    main()