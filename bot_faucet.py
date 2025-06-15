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
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)
log = logging.getLogger("rich")

def retry_on_failure(max_retries=3, delay=5):
    """Decorator untuk mencoba ulang fungsi jika gagal."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        log.error(f"Percobaan {attempt + 1}/{max_retries} gagal: {e}")
                        log.info(f"Mencoba ulang dalam {delay} detik...")
                        time.sleep(delay)
                    else:
                        log.error(f"Semua percobaan gagal: {e}")
                        raise
        return wrapper
    return decorator

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

# Konfigurasi Telegram
TELEGRAM_BOT_TOKEN = "7519988044:AAFXRo2bDE99y46Fl_E_H9vbNNSW23mLvXM"
TELEGRAM_CHAT_ID = "1433257992"

def create_wallet():
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    return account.address, private_key

@retry_on_failure(max_retries=3, delay=5)
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

@retry_on_failure(max_retries=3, delay=5)
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

@retry_on_failure(max_retries=3, delay=5)
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
            return True, data.get('txhash')
        else:
            log.error(f"[Thread {thread_id}] [bold red]❌ Klaim gagal:[/] {data.get('message')}")
            return False, data.get('message')
    except requests.exceptions.JSONDecodeError:
        log.error(f"[Thread {thread_id}] [bold red]❌ Gagal mem-parse response JSON. Status: {response.status_code}, Response: {response.text}[/]")
        return False, "JSON Parse Error"
    except Exception as e:
        log.error(f"[Thread {thread_id}] [bold red]❌ Exception saat klaim: {e}[/]")
        return False, str(e)

@retry_on_failure(max_retries=3, delay=5)
def send_eth(private_key, from_address, thread_id):
    log.info(f"[Thread {thread_id}] [cyan]💸 Mempersiapkan pengiriman ETH dari {from_address[:10]}...[/]")
    web3 = Web3(Web3.HTTPProvider(RPC_URL, {"proxies": BASE_PROXY}))
    if not web3.is_connected():
        raise Exception(f"Gagal terhubung ke RPC {RPC_URL}")
        
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
    return web3.to_hex(tx_hash)

@retry_on_failure(max_retries=3, delay=5)
def check_balance(address, thread_id):
    web3 = Web3(Web3.HTTPProvider(RPC_URL, {"proxies": BASE_PROXY}))
    if not web3.is_connected():
        raise Exception(f"Gagal terhubung ke RPC untuk cek saldo.")
    balance_wei = web3.eth.get_balance(address)
    balance_eth = web3.from_wei(balance_wei, 'ether')
    log.info(f"[Thread {thread_id}] 💰 Saldo [yellow]{address[:10]}[/]: [bold green]{balance_eth:.4f} ETH[/]")
    return balance_eth

def send_telegram_message(message):
    """Mengirim pesan ke Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        log.error(f"Gagal mengirim notifikasi Telegram: {e}")

def get_wallet_balance(address):
    """Mendapatkan balance wallet dalam ETH."""
    try:
        web3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not web3.is_connected():
            return 0
        balance_wei = web3.eth.get_balance(address)
        return web3.from_wei(balance_wei, 'ether')
    except Exception:
        return 0

def send_telegram_summary(wallet_results):
    """Mengirim rekap hasil semua wallet ke Telegram."""
    message = """
📊 <b>REKAP HASIL FAUCET</b>

"""
    total_balance = 0
    total_success = 0
    total_failed = 0
    
    for wallet, result in wallet_results.items():
        account_name = result["account_name"]
        balance = result["balance"]
        total_balance += balance
        if result["success"]:
            total_success += 1
        else:
            total_failed += 1
            
        status = "✅ Berhasil" if result["success"] else f"❌ Gagal: {result['error']}"
        message += f"""
👛 Account: <b>{account_name}</b>
📝 Wallet: <code>{wallet}</code>
💰 Balance: <b>{balance:.4f} ETH</b>
📊 Status: {status}
"""
        if result.get("tx_hashes"):
            message += "🔗 Tx Hashes:\n"
            for tx in result["tx_hashes"]:
                message += f"<code>{tx}</code>\n"
        message += "➖➖➖➖➖➖➖➖➖➖\n"
    
    # Tambahkan ringkasan di akhir
    message += f"""
<b>RINGKASAN</b>
💰 Total Balance: <b>{total_balance:.4f} ETH</b>
✅ Berhasil: {total_success}
❌ Gagal: {total_failed}
👥 Total Wallet: {len(wallet_results)}
"""
    
    send_telegram_message(message)

def process_wallet(account, thread_id, stop_event):
    """Proses satu wallet dengan retry mechanism."""
    private_key = account["private_key"]
    proxy = account["proxy"]
    account_name = account["name"]
    address = Account.from_key(private_key).address
    
    wallet_result = {
        "account_name": account_name,
        "success": False,
        "error": None,
        "tx_hashes": [],
        "balance": get_wallet_balance(address)
    }
    
    log.info(f"[Thread {thread_id}] [bold blue]Memulai proses untuk wallet {account_name}...[/]")
    
    while not stop_event.is_set():
        try:
            # Setup session dengan proxy
            session = requests.Session()
            session.proxies.update({
                "http": proxy,
                "https": proxy
            })
            
            # Cek saldo
            check_balance(address, thread_id)
            
            # Proses CAPTCHA
            cap_id = submit_captcha(session, thread_id)
            cap_token = get_captcha_result(session, cap_id, thread_id)
            
            # Klaim
            success, tx_hash = claim(session, address, cap_token, thread_id)
            if success and tx_hash:
                wallet_result["tx_hashes"].append(tx_hash)
                # Kirim ETH
                eth_tx_hash = send_eth(private_key, address, thread_id)
                if eth_tx_hash:
                    wallet_result["tx_hashes"].append(eth_tx_hash)
                wallet_result["success"] = True
            
            # Update balance
            wallet_result["balance"] = get_wallet_balance(address)
            
            # Tunggu 24 jam
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
                    
        except Exception as e:
            log.error(f"[Thread {thread_id}] [red]❗ Error pada wallet {account_name}: {e}[/]")
            wallet_result["error"] = str(e)
            time.sleep(60)  # Tunggu 1 menit sebelum retry jika terjadi error
    
    return wallet_result

def run_parallel_faucet(stop_event):
    """Menjalankan faucet secara parallel untuk semua wallet."""
    if not ACCOUNTS:
        log.error("❌ Tidak ada wallet yang ditemukan di config.json.")
        return

    # Kirim notifikasi awal
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send_telegram_message(f"""
🚀 <b>MULAI PROSES FAUCET</b>

⏰ Waktu Mulai: {start_time}
👥 Total Wallet: {len(ACCOUNTS)}
""")
    
    # Buat thread untuk setiap wallet
    threads = []
    wallet_results = {}
    
    for i, account in enumerate(ACCOUNTS):
        thread = threading.Thread(
            target=lambda: wallet_results.update({Account.from_key(account["private_key"]).address: process_wallet(account, i + 1, stop_event)}),
        )
        threads.append(thread)
        thread.start()
        time.sleep(2)  # Delay kecil antara setiap thread
    
    # Tunggu semua thread selesai
    for thread in threads:
        thread.join()
    
    # Kirim rekap hasil ke Telegram
    send_telegram_summary(wallet_results)
    
    info("Semua wallet telah selesai diproses!")

def main():
    title = Panel(
        Text("MEGAETH FAUCET BOT", justify="center", style="bold magenta"),
        title="[bold green]By: Bény G.[/]",
        subtitle="[cyan]v2.2 with Parallel Processing[/]"
    )
    console.print(title)

    menu_table = Table(show_header=False, box=None)
    menu_table.add_row("[bold cyan]1.[/]", "Load dari config.json (klaim tiap 24 jam)")
    console.print(Panel(menu_table, title="[yellow]PILIH FITUR[/]", border_style="yellow"))

    mode = console.input("[bold green]Pilih fitur (1): [/]").strip()
    stop_event = threading.Event()

    try:
        if mode == "1":
            run_parallel_faucet(stop_event)
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