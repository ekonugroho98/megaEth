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
        Text("MEGAETH FAUCET BOT", justify="center", style="bold magenta"),
        title="[bold green]By: Bény G.[/]",
        subtitle="[cyan]v3.0 - Single Mode[/]"
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