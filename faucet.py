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
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False, show_time=False, markup=False)]
)
log = logging.getLogger("rich")

def load_captcha_key(filename="captcha_key.txt"):
    """Memuat API key CAPTCHA dari file teks."""
    try:
        with open(filename, "r") as f:
            key = f.readline().strip()
            if not key:
                log.critical(f"Error: File '{filename}' kosong. Harap isi dengan API key Anda.")
                sys.exit(1)
            log.info(f"API Key CAPTCHA berhasil dimuat dari {filename}.")
            return key
    except FileNotFoundError:
        log.critical(f"Error: File '{filename}' tidak ditemukan. Harap buat file tersebut dan isi dengan API key Anda.")
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
                log.warning(f"File proxy '{filename}' kosong.")
                return []
            log.info(f"Berhasil memuat {len(proxies)} proxy dari {filename}.")
            return proxies
    except FileNotFoundError:
        log.warning(f"File proxy '{filename}' tidak ditemukan.")
        return []

def load_keys(filename="private_keys.txt"):
    try:
        with open(filename, "r") as f:
            keys = [line.strip() for line in f if line.strip()]
            log.info(f"Berhasil memuat {len(keys)} kunci dari {filename}.")
            return keys
    except FileNotFoundError:
        log.warning(f"File '{filename}' tidak ditemukan.")
        return []

def submit_captcha(session, short_addr):
    """Membuat task penyelesaian Turnstile di Anti-Captcha."""
    log.info(f"[{short_addr}] Mengirim permintaan CAPTCHA...")
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
            
        log.info(f"[{short_addr}] CAPTCHA diterima. ID: {task_id}")
        return task_id
    except Exception as e:
        raise Exception(f"Error saat menghubungi Anti-Captcha: {e}")

def get_captcha_result(session, task_id, short_addr):
    """Mendapatkan hasil penyelesaian CAPTCHA dari Anti-Captcha."""
    payload = {
        "clientKey": APIKEY,
        "taskId": task_id
    }
    
    log.info(f"[{short_addr}] Menunggu hasil Anti-Captcha...")
    # Timeout 120 detik (40 * 3 detik)
    for _ in range(40):
        time.sleep(3)
        try:
            res = session.post(ANTICAPTCHA_GET_RESULT_URL, json=payload, timeout=20).json()
            
            if res.get("errorId") != 0:
                raise Exception(f"Gagal mendapatkan hasil - {res.get('errorCode')}: {res.get('errorDescription')}")

            status_val = res.get("status")
            if status_val == "ready":
                log.info(f"[{short_addr}] CAPTCHA berhasil diselesaikan.")
                token = res.get("solution", {}).get("token")
                if not token:
                    raise Exception("Token tidak ditemukan di response Anti-Captcha.")
                return token
            
            if status_val == "processing":
                continue # Lanjutkan menunggu

            # Status lain tidak diharapkan
            raise Exception(f"Status tidak diketahui dari Anti-Captcha: {status_val}")

        except Exception as e:
            log.error(f"[{short_addr}] Error saat polling hasil: {e}")
            # Lanjutkan mencoba sampai timeout
            continue

    raise Exception("Timeout saat menunggu hasil CAPTCHA dari Anti-Captcha.")

def claim(session, addr, token, short_addr):
    log.info(f"[{short_addr}] Mencoba melakukan klaim...")
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
            log.info(f"[{short_addr}] Klaim sukses! Tx: {data.get('txhash')}")
            return True
        else:
            log.error(f"[{short_addr}] Klaim gagal: {data.get('message')}")
            return False
    except requests.exceptions.JSONDecodeError:
        log.error(f"[{short_addr}] Gagal mem-parse response JSON. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        log.error(f"[{short_addr}] Exception saat klaim: {e}")
    return False

def check_balance(address, proxy, short_addr):
    request_kwargs = {'proxies': {'http': f"http://{proxy}", 'https': f"http://{proxy}"}} if proxy else {}
    web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs=request_kwargs))
    if not web3.is_connected():
        log.error(f"[{short_addr}] Gagal terhubung ke RPC.")
        return 0
    balance_wei = web3.eth.get_balance(address)
    balance_eth = web3.from_wei(balance_wei, 'ether')
    log.info(f"[{short_addr}] Saldo: {balance_eth:.4f} ETH")
    return balance_eth
    
def process_key_looping(private_key, proxy, thread_id, stop_event):
    account = Account.from_key(private_key)
    address = account.address
    short_addr = f"{address[:6]}..{address[-4:]}"
    proxy_display = proxy.split('@')[-1] if proxy else "Tidak ada"
    log.info(f"Thread {thread_id}: Memulai wallet {short_addr} | Proxy: {proxy_display}")
    
    while not stop_event.is_set():
        session = requests.Session()
        if proxy:
            session.proxies.update({"http": f"http://{proxy}", "https": f"http://{proxy}"})
        
        try:
            check_balance(address, proxy, short_addr)
            cap_id = submit_captcha(session, short_addr)
            cap_token = get_captcha_result(session, cap_id, short_addr)
            claim(session, address, cap_token, short_addr)
        except Exception as e:
            log.error(f"[{short_addr}] Error pada siklus: {e}")
        finally:
            session.close()

        wait_seconds = 86400
        log.info(f"[{short_addr}] Siklus selesai. Menunggu 24 jam untuk klaim berikutnya.")

        # Gunakan pendekatan sederhana tanpa console.status untuk menghindari konflik thread
        for i in range(wait_seconds):
            if stop_event.is_set(): 
                break
            time.sleep(1)

def run_faucet_for_all_keys_sequential(stop_event):
    """Versi sequential - memproses wallet satu per satu"""
    log.info("Memulai bot faucet (SEQUENTIAL MODE)...")
    keys = load_keys()
    if not keys:
        log.error("File private_keys.txt kosong atau tidak ditemukan. Bot akan berhenti.")
        return
    
    proxies = load_proxies()
    if proxies and len(keys) > len(proxies):
        log.warning(f"Peringatan: Jumlah kunci ({len(keys)}) lebih banyak dari jumlah proxy ({len(proxies)}). Beberapa kunci akan dijalankan tanpa proxy.")

    cycle_count = 0
    while not stop_event.is_set():
        cycle_count += 1
        log.info(f"=== MEMULAI SIKLUS {cycle_count} ===")
        
        successful_wallets = 0
        failed_wallets = 0
        
        for i, key in enumerate(keys):
            if stop_event.is_set():
                log.info("Sinyal berhenti diterima. Menghentikan proses...")
                break
                
            proxy = proxies[i] if proxies and i < len(proxies) else None
            log.info(f"Memproses wallet {i+1}/{len(keys)}")
            
            # Proses satu kali klaim untuk wallet ini
            account = Account.from_key(key)
            address = account.address
            short_addr = f"{address[:6]}..{address[-4:]}"
            proxy_display = proxy.split('@')[-1] if proxy else "Tidak ada"
            log.info(f"Thread {i+1}: Memulai wallet {short_addr} | Proxy: {proxy_display}")
            
            session = requests.Session()
            if proxy:
                session.proxies.update({"http": f"http://{proxy}", "https": f"http://{proxy}"})
            
            try:
                check_balance(address, proxy, short_addr)
                cap_id = submit_captcha(session, short_addr)
                cap_token = get_captcha_result(session, cap_id, short_addr)
                if claim(session, address, cap_token, short_addr):
                    successful_wallets += 1
                    log.info(f"[{short_addr}] Wallet {i+1} berhasil diproses.")
                else:
                    failed_wallets += 1
                    log.warning(f"[{short_addr}] Wallet {i+1} gagal diproses.")
            except Exception as e:
                failed_wallets += 1
                log.error(f"[{short_addr}] Error pada siklus: {e}")
            finally:
                session.close()
            
            # Jeda antar wallet (opsional)
            if i < len(keys) - 1 and not stop_event.is_set():
                log.info(f"Menunggu 5 detik sebelum lanjut ke wallet berikutnya...")
                time.sleep(5)
        
        # Setelah semua wallet diproses, tunggu 24 jam sebelum siklus berikutnya
        if not stop_event.is_set():
            log.info(f"=== SIKLUS {cycle_count} SELESAI ===")
            log.info(f"Ringkasan: {successful_wallets} wallet berhasil, {failed_wallets} wallet gagal")
            log.info("Semua wallet telah diproses. Menunggu 24 jam untuk siklus berikutnya...")
            for i in range(86400):  # 24 jam
                if stop_event.is_set():
                    break
                time.sleep(1)

def run_faucet_for_all_keys(stop_event):
    """Versi parallel - memproses semua wallet bersamaan"""
    log.info("Memulai bot faucet (PARALLEL MODE)...")
    keys = load_keys()
    if not keys:
        log.error("File private_keys.txt kosong atau tidak ditemukan. Bot akan berhenti.")
        return
    
    proxies = load_proxies()
    if proxies and len(keys) > len(proxies):
        log.warning(f"Peringatan: Jumlah kunci ({len(keys)}) lebih banyak dari jumlah proxy ({len(proxies)}). Beberapa kunci akan dijalankan tanpa proxy.")

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
        Text("MEGAETH FAUCET BOT", justify="center"),
    )
    console.print(title)

    # Pilihan mode
    console.print("\n[bold cyan]Pilih mode operasi:[/bold cyan]")
    console.print("1. [bold green]PARALLEL[/bold green] - Semua wallet berjalan bersamaan (default)")
    console.print("2. [bold yellow]SEQUENTIAL[/bold yellow] - Wallet diproses satu per satu")
    
    try:
        choice = input("\nMasukkan pilihan (1 atau 2, default=1): ").strip()
        if choice == "2":
            sequential_mode = True
            console.print("[bold yellow]Mode SEQUENTIAL dipilih[/bold yellow]")
        else:
            sequential_mode = False
            console.print("[bold green]Mode PARALLEL dipilih[/bold green]")
    except (KeyboardInterrupt, EOFError):
        sequential_mode = False
        console.print("[bold green]Mode PARALLEL dipilih (default)[/bold green]")

    stop_event = threading.Event()

    try:
        if sequential_mode:
            run_faucet_for_all_keys_sequential(stop_event)
        else:
            run_faucet_for_all_keys(stop_event)
    except (KeyboardInterrupt, EOFError):
        log.warning("\nProgram dihentikan oleh pengguna. Mengirim sinyal berhenti ke semua thread...")
        stop_event.set()
        log.info("Program telah dihentikan.")

if __name__ == "__main__":
    main()