import requests
import time
import threading
import logging
import sys
from eth_account import Account
from web3 import Web3
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler

console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)
log = logging.getLogger("rich")

def load_captcha_key(filename="captcha_key.txt"):
    """Memuat API key CAPTCHA dari file teks."""
    try:
        with open(filename, "r") as f:
            key = f.readline().strip()
            if not key:
                log.critical(f"[bold red]❌ Error: File '{filename}' kosong. Harap isi dengan API key Anda.[/]")
                sys.exit(1)
            log.info(f"[bold green]✔️ API Key CAPTCHA berhasil dimuat dari {filename}.[/]")
            return key
    except FileNotFoundError:
        log.critical(f"[bold red]❌ Error: File '{filename}' tidak ditemukan. Harap buat file tersebut dan isi dengan API key Anda.[/]")
        sys.exit(1)

APIKEY = load_captcha_key()

TURNSTILE_SITEKEY = "0x4AAAAAABA4JXCaw9E2Py-9"
TURNSTILE_PAGE_URL = "https://testnet.megaeth.com/"
MEGAETH_API_URL = "https://carrot.megaeth.com/claim"
RPC_URL = "https://carrot.megaeth.com/rpc"

# URL untuk Anti-Captcha
ANTICAPTCHA_CREATE_TASK_URL = "https://api.anti-captcha.com/createTask"
ANTICAPTCHA_GET_RESULT_URL = "https://api.anti-captcha.com/getTaskResult"

def load_proxies(filename="proxies.txt"):
    """Memuat daftar proxy dari file."""
    try:
        with open(filename, "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
            if not proxies:
                log.warning(f"[yellow]⚠️ File proxy '{filename}' kosong.[/]")
                return []
            log.info(f"[green]🔑 Berhasil memuat {len(proxies)} proxy dari {filename}[/]")
            return proxies
    except FileNotFoundError:
        log.warning(f"[yellow]⚠️ File proxy '{filename}' tidak ditemukan.[/]")
        return []

def load_keys(filename="private_keys.txt"):
    try:
        with open(filename, "r") as f:
            keys = [line.strip() for line in f if line.strip()]
            log.info(f"[green]🔑 Berhasil memuat {len(keys)} kunci dari {filename}[/]")
            return keys
    except FileNotFoundError:
        log.warning(f"[yellow]⚠️ File '{filename}' tidak ditemukan.[/]")
        return []

def submit_captcha(session, thread_id):
    """Membuat task penyelesaian Turnstile di Anti-Captcha."""
    log.info(f"[Thread {thread_id}] [yellow]📤 Membuat task di Anti-Captcha...[/]")
    payload = {
        "clientKey": APIKEY,
        "task": {
            "type": "TurnstileTaskProxyless",
            "websiteURL": TURNSTILE_PAGE_URL,
            "websiteKey": TURNSTILE_SITEKEY
        }
    }
    try:
        res = session.post(ANTICAPTCHA_CREATE_TASK_URL, json=payload, timeout=20).json()
        if res.get("errorId") != 0:
            raise Exception(f"Gagal membuat task - {res.get('errorCode')}: {res.get('errorDescription')}")
        
        task_id = res.get("taskId")
        if not task_id:
            raise Exception("Gagal mendapatkan taskId dari response Anti-Captcha.")
            
        log.info(f"[Thread {thread_id}] [green]✔️ Task Anti-Captcha diterima. ID: {task_id}[/]")
        return task_id
    except Exception as e:
        raise Exception(f"Error saat menghubungi Anti-Captcha: {e}")

def get_captcha_result(session, task_id, thread_id):
    """Mendapatkan hasil penyelesaian CAPTCHA dari Anti-Captcha."""
    payload = {
        "clientKey": APIKEY,
        "taskId": task_id
    }
    with console.status(f"[bold yellow][Thread {thread_id}] ⏳ Menunggu hasil Anti-Captcha...", spinner="dots") as status:
        # Timeout 120 detik (40 * 3 detik)
        for _ in range(40):
            time.sleep(3)
            try:
                res = session.post(ANTICAPTCHA_GET_RESULT_URL, json=payload, timeout=20).json()
                
                if res.get("errorId") != 0:
                    raise Exception(f"Gagal mendapatkan hasil - {res.get('errorCode')}: {res.get('errorDescription')}")

                status_val = res.get("status")
                if status_val == "ready":
                    log.info(f"[Thread {thread_id}] [green]✅ CAPTCHA berhasil diselesaikan![/]")
                    token = res.get("solution", {}).get("token")
                    if not token:
                        raise Exception("Token tidak ditemukan di response Anti-Captcha.")
                    return token
                
                if status_val == "processing":
                    continue # Lanjutkan menunggu

                # Status lain tidak diharapkan
                raise Exception(f"Status tidak diketahui dari Anti-Captcha: {status_val}")

            except Exception as e:
                log.error(f"[Thread {thread_id}] [red]Error saat polling hasil: {e}[/]")
                # Lanjutkan mencoba sampai timeout
                continue

    raise Exception("Timeout saat menunggu hasil CAPTCHA dari Anti-Captcha.")

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

def check_balance(address, proxy, thread_id):
    request_kwargs = {'proxies': {'http': f"http://{proxy}", 'https': f"http://{proxy}"}} if proxy else {}
    web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs=request_kwargs))
    if not web3.is_connected():
        log.error(f"[Thread {thread_id}] [red]❌ Gagal terhubung ke RPC untuk cek saldo.[/]")
        return 0
    balance_wei = web3.eth.get_balance(address)
    balance_eth = web3.from_wei(balance_wei, 'ether')
    log.info(f"[Thread {thread_id}] 💰 Saldo [yellow]{address[:10]}[/]: [bold green]{balance_eth:.4f} ETH[/]")
    return balance_eth
    
def process_key_looping(private_key, proxy, thread_id, stop_event):
    account = Account.from_key(private_key)
    address = account.address
    proxy_display = proxy.split('@')[-1] if proxy else "Tidak ada"
    log.info(f"[Thread {thread_id}] [bold blue]Memulai loop untuk wallet {address[:10]}... | Proxy: {proxy_display}[/]")
    
    while not stop_event.is_set():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.info(f"\n[Thread {thread_id}] [magenta]({now_str})[/] Memulai siklus untuk [yellow]{address[:10]}[/]")
        session = requests.Session()
        if proxy:
            session.proxies.update({"http": f"http://{proxy}", "https": f"http://{proxy}"})
        
        try:
            check_balance(address, proxy, thread_id)
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

def run_faucet_for_all_keys(stop_event):
    log.info("[bold green]Memulai bot faucet...[/]")
    keys = load_keys()
    if not keys:
        log.error("❌ File private_keys.txt kosong atau tidak ditemukan. Bot akan berhenti.")
        return
    
    proxies = load_proxies()
    if proxies and len(keys) > len(proxies):
        log.warning(f"[bold yellow]⚠️ Jumlah kunci ({len(keys)}) lebih banyak dari jumlah proxy ({len(proxies)}). Beberapa kunci akan dijalankan tanpa proxy.[/]")

    threads = []
    for i, key in enumerate(keys):
        proxy = proxies[i] if proxies and i < len(proxies) else None
        t = threading.Thread(target=process_key_looping, args=(key, proxy, i + 1, stop_event))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

def main():
    title = Panel(
        Text("MEGAETH FAUCET BOT", justify="center", style="bold green"),
    )
    console.print(title)

    stop_event = threading.Event()

    try:
        run_faucet_for_all_keys(stop_event)
    except (KeyboardInterrupt, EOFError):
        log.warning("\n[bold yellow]⚠️ Program dihentikan oleh pengguna. Mengirim sinyal berhenti ke semua thread...[/]")
        stop_event.set()
        log.info("[bold red]🛑 Program telah dihentikan.[/]")

if __name__ == "__main__":
    main()