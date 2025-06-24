import json
import os
import time
import requests
from dotenv import load_dotenv
from web3 import Web3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
import sys
import threading
from datetime import datetime

console = Console()

def info(msg): console.print(f"[bold cyan][*][/bold cyan] {msg}")
def success(msg): console.print(f"[bold green][+][/bold green] {msg}")
def error(msg): console.print(f"[bold red][!][/bold red] {msg}")
def warning(msg): console.print(f"[bold yellow][-][/bold yellow] {msg}")
def prompt(msg): return console.input(f"[bold yellow]>> {msg}[/bold yellow]")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config():
    """Memuat konfigurasi dari file config.json."""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        # Validasi konfigurasi Telegram
        if "telegram" not in config:
            config["telegram"] = {
                "enabled": False,
                "bot_token": "",
                "chat_id": ""
            }
        elif config["telegram"]["enabled"]:
            if not config["telegram"].get("bot_token"):
                raise ValueError("Telegram bot token tidak ditemukan dalam config")
            if not config["telegram"].get("chat_id"):
                raise ValueError("Telegram chat ID tidak ditemukan dalam config")
                
        console.print("[bold green]✔️ Konfigurasi dari config.json berhasil dimuat.[/]")
        return config
    except FileNotFoundError:
        console.print("[bold red]❌ Error: File 'config.json' tidak ditemukan. Harap buat file tersebut sesuai contoh.[/]")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print("[bold red]❌ Error: Format file 'config.json' tidak valid. Pastikan format JSON sudah benar.[/]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/]")
        sys.exit(1)

config = load_config()
ANTI_CAPTCHA_KEY = config["ANTI_CAPTCHA_KEY"]

RPC = 'https://carrot.megaeth.com/rpc'
CHAIN = 6342

# Konfigurasi Telegram
TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]

def send_telegram_message(message):
    """Mengirim pesan ke Telegram."""
    if not config["telegram"]["enabled"]:
        return
        
    try:
        url = f"https://api.telegram.org/bot{config['telegram']['bot_token']}/sendMessage"
        data = {
            "chat_id": config["telegram"]["chat_id"],
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        error(f"Gagal mengirim notifikasi Telegram: {e}")

def get_account_name(address):
    """Mendapatkan nama account dari config.json berdasarkan address."""
    for acc in config["account"]:
        if Web3.to_checksum_address(acc["private_key"]) == Web3.to_checksum_address(address):
            return acc["name"]
    return address[:10]  # Return first 10 chars of address if name not found

def send_telegram_status(wallet_address, status, tx_hash=None):
    """Mengirim status operasi ke Telegram."""
    account_name = get_account_name(wallet_address)
    message = f"""
🔔 <b>Status Operasi</b>

👛 Account: <b>{account_name}</b>
📝 Wallet: <code>{wallet_address}</code>
📊 Status: {status}
"""
    if tx_hash:
        message += f"🔗 Tx Hash: <code>{tx_hash}</code>"
    
    send_telegram_message(message)

# Definisikan ABI terlebih dahulu
PAIR_ABI = json.loads("""[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"}]""")
FACTORY_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"}],"name":"getPair","outputs":[{"name":"pair","type":"address"}],"stateMutability":"view","type":"function"}]""")
ERC20_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"}]""")
ROUTER_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"amountIn","type":"uint256"},{"name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"name":"","type":"uint256[]"}],"type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"WETH","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amountTokenDesired","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"payable","type":"function"}]""")
WETH_DEPOSIT_ABI = [{"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"}]

# Inisialisasi Web3
info("Menyambungkan ke RPC...")
w3 = Web3(Web3.HTTPProvider(RPC))
if not w3.is_connected(): error("Koneksi RPC gagal!"); exit()
if w3.eth.chain_id != CHAIN: error(f"Chain ID tidak cocok: diharapkan {CHAIN}, didapat {w3.eth.chain_id}"); exit()
success("RPC terhubung dengan sukses.")

def load_private_keys():
    pk_list = []
    proxy_list = []
    try:
        if "account" in config:
            info("Memuat private key dan proxy dari [bold]config.json[/bold]")
            for acc in config["account"]:
                pk_list.append(acc["private_key"])
                proxy_list.append(acc["proxy"])
    except Exception as e:
        error(f"Error saat memuat dari config.json: {e}")
        sys.exit(1)

    if not pk_list:
        error("Tidak ada private key yang ditemukan di config.json.")
        sys.exit(1)
    return pk_list, proxy_list

PK_LIST, PROXY_LIST = load_private_keys()
accounts = [w3.eth.account.from_key(pk) for pk in PK_LIST]
mass_swap_enabled = False
A, PK, PROXY = None, None, None

# Inisialisasi kontrak dan konstanta lainnya
ROUTER_ADDR = Web3.to_checksum_address("0xa6b579684e943f7d00d616a48cf99b5147fc57a5")
router = w3.eth.contract(address=ROUTER_ADDR, abi=ROUTER_ABI)
WETH_ADDR = router.functions.WETH().call()
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
GAS_P = w3.to_wei('0.001', 'gwei')
GAS_AP, GAS_SW = 200_000, 500_000
SLIPPAGE = 0.11
TOKENS = {}

def get_web3_with_proxy(proxy):
    return Web3(Web3.HTTPProvider(RPC, request_kwargs={
        "proxies": {
            "http": proxy,
            "https": proxy
        }
    }))

def wait_for_tx(tx_hash, message):
    with console.status(f"[bold green]{message} [dim]{tx_hash.hex()}[/dim][/bold green]", spinner="dots") as status:
        try:
            w3_proxy = get_web3_with_proxy(PROXY)
            receipt = w3_proxy.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            return receipt
        except Exception as e:
            error(f"Timeout atau error saat menunggu transaksi: {e}")
            return None

def select_wallets():
    info("Pilih dompet yang akan digunakan untuk operasi berikutnya:")
    sel_str = prompt("Masukkan indeks (misal: 0 atau 0,2 atau 'all'): ").strip().lower()
    selected_indices = []
    if sel_str in ('all', ''): selected_indices = list(range(len(accounts)))
    else:
        for part in sel_str.split(','):
            try:
                i = int(part.strip())
                if 0 <= i < len(accounts) and i not in selected_indices: selected_indices.append(i)
            except ValueError: pass
    if not selected_indices: warning("Pilihan tidak valid, menggunakan dompet 0 secara default."); selected_indices = [0]
    sel_accounts = [accounts[i] for i in selected_indices]
    sel_pks = [PK_LIST[i] for i in selected_indices]
    sel_proxies = [PROXY_LIST[i] for i in selected_indices]
    addresses = ", ".join(f"[cyan]{acc.address}[/cyan]" for acc in sel_accounts)
    success(f"Dompet terpilih untuk proses ini: {addresses}")
    return sel_accounts, sel_pks, sel_proxies

def display_wallet_summary():
    table = Table(title="Ringkasan Dompet", border_style="magenta", show_header=True, header_style="bold cyan")
    table.add_column("Indeks", style="cyan", width=6)
    table.add_column("Alamat Dompet", style="white")
    table.add_column("Saldo ETH", style="green", justify="right")
    table.add_column("Proxy", style="yellow")
    for idx, (acc, proxy) in enumerate(zip(accounts, PROXY_LIST)):
        try:
            w3_proxy = get_web3_with_proxy(proxy)
            bal_wei = w3_proxy.eth.get_balance(acc.address)
            bal_eth = w3_proxy.from_wei(bal_wei, 'ether')
            table.add_row(str(idx), acc.address, f"{bal_eth:.6f} ETH", proxy)
        except Exception:
            table.add_row(str(idx), acc.address, "[red]Gagal[/red]", proxy)
    console.print(table)

def fetch_and_load_tokens():
    global TOKENS
    API_URL = "https://api-testnet.gte.xyz/v1/markets?sortBy=volume&limit=100"
    headers = {
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://testnet.gte.xyz',
        'referer': 'https://testnet.gte.xyz/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
    }
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            with console.status(f"[bold yellow]Memuat data token (Percobaan {attempt + 1}/{max_retries})...[/bold yellow]", spinner="dots"):
                resp = requests.get(API_URL, headers=headers, timeout=30)  # Increased timeout
                resp.raise_for_status()
                markets = resp.json()
                
                # Proses data token dari response
                for market in markets:
                    # Proses base token
                    base_token = market.get('baseToken', {})
                    if base_token:
                        symbol = base_token.get('symbol', '').upper().strip()
                        if symbol:
                            addr = Web3.to_checksum_address(base_token['address'])
                            TOKENS[symbol] = {
                                "address": addr,
                                "decimals": base_token.get('decimals', 18)
                            }
                    
                    # Proses quote token
                    quote_token = market.get('quoteToken', {})
                    if quote_token:
                        symbol = quote_token.get('symbol', '').upper().strip()
                        if symbol:
                            addr = Web3.to_checksum_address(quote_token['address'])
                            TOKENS[symbol] = {
                                "address": addr,
                                "decimals": quote_token.get('decimals', 18)
                            }
                
                # Tambahkan ETH dan WETH
                TOKENS["ETH"] = {"address": None, "decimals": 18}
                TOKENS["WETH"] = {"address": WETH_ADDR, "decimals": 18}
                
                success(f"Berhasil memuat {len(TOKENS)} token.")
                return
                
        except requests.exceptions.RequestException as e:
            error(f"Gagal memuat data token (Percobaan {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                warning(f"Mencoba ulang dalam {retry_delay} detik...")
                time.sleep(retry_delay)
            else:
                warning("Menggunakan data token minimal (ETH dan WETH saja)")
                # Tetap tambahkan ETH dan WETH meskipun gagal
                TOKENS["ETH"] = {"address": None, "decimals": 18}
                TOKENS["WETH"] = {"address": WETH_ADDR, "decimals": 18}
                success("Berhasil memuat token minimal (ETH dan WETH).")

def select_token_from_list(prompt_title, exclude_symbols=None):
    if exclude_symbols is None: exclude_symbols = []
    sorted_symbols = sorted(
        [s for s in TOKENS if s not in exclude_symbols],
        key=lambda s: (s not in ['ETH', 'WETH'], s)
    )
    if not sorted_symbols: error("Tidak ada token yang tersedia untuk dipilih."); return None
    table = Table(title=f"[bold cyan]{prompt_title}[/bold cyan]", border_style="cyan")
    table.add_column("No.", style="yellow"); table.add_column("Simbol", style="white"); table.add_column("Alamat Kontrak", style="dim")
    for i, symbol in enumerate(sorted_symbols):
        addr = TOKENS[symbol]['address'] if TOKENS[symbol]['address'] else "Native Token"
        table.add_row(str(i + 1), symbol, addr)
    while True:
        console.print(table)
        choice = prompt(f"Pilih nomor token (1-{len(sorted_symbols)}) atau 'q' untuk batal: ")
        if choice.lower() == 'q': return None
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(sorted_symbols): return sorted_symbols[choice_idx]
            else: error("Nomor tidak valid, silakan coba lagi.")
        except ValueError: error("Input tidak valid, masukkan nomor.")

def chk_native(need):
    balance = w3.eth.get_balance(A)
    if balance < need: error(f"Saldo ETH tidak cukup. Butuh: {w3.from_wei(need, 'ether')} ETH"); return False
    return True

def retry_on_failure(func, max_retries=3, delay=5):
    """Decorator untuk mencoba ulang fungsi jika gagal."""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    error(f"Percobaan {attempt + 1}/{max_retries} gagal: {e}")
                    info(f"Mencoba ulang dalam {delay} detik...")
                    time.sleep(delay)
                else:
                    error(f"Semua percobaan gagal: {e}")
                    raise
    return wrapper

def send_telegram_summary(wallet_results):
    """Mengirim rekap hasil semua wallet ke Telegram."""
    message = """
📊 <b>REKAP HASIL SEMUA WALLET</b>

"""
    for wallet, result in wallet_results.items():
        account_name = get_account_name(wallet)
        status = "✅ Berhasil" if result["success"] else f"❌ Gagal: {result['error']}"
        message += f"""
👛 Account: <b>{account_name}</b>
📝 Wallet: <code>{wallet}</code>
📊 Status: {status}
"""
        if result.get("tx_hashes"):
            message += "🔗 Tx Hashes:\n"
            for tx in result["tx_hashes"]:
                message += f"<code>{tx}</code>\n"
        message += "➖➖➖➖➖➖➖➖➖➖\n"
    
    send_telegram_message(message)

def process_wallet(acct, pk, proxy, wallet_index, total_wallets):
    global A, PK, PROXY
    A, PK, PROXY = acct.address, pk, proxy
    console.print(Rule(f"Memproses Dompet {wallet_index+1}/{total_wallets}: {A}", style="bold green"))
    
    wallet_result = {
        "success": False,
        "error": None,
        "tx_hashes": []
    }
    
    try:
        # 1. Swap ETH ke WETH
        info(f"Task 1: Swap 0.001 ETH ke WETH")
        amount_wei = w3.to_wei(0.001, 'ether')
        tx_hash = do_swap('ETH', 'WETH', amount_wei)
        if tx_hash:
            wallet_result["tx_hashes"].append(tx_hash)
        time.sleep(1)
        
        # 2. Add Liquidity
        info(f"Task 2: Add Liquidity 0.001 ETH + WETH")
        eth_wei = w3.to_wei(0.001, 'ether')
        tx_hash = add_liquidity('WETH', eth_wei)
        if tx_hash:
            wallet_result["tx_hashes"].append(tx_hash)
        time.sleep(1)
        
        # 3. Swap semua token ke ETH
        info("Task 3: Swap semua token ke ETH")
        for symbol, token_data in TOKENS.items():
            if symbol in ["ETH", "WETH"] or not token_data.get("address"): continue
            try:
                contract = w3.eth.contract(address=token_data["address"], abi=ERC20_ABI)
                balance = contract.functions.balanceOf(A).call()
                if balance > 0:
                    human_bal = balance / (10**token_data.get('decimals', 18))
                    info(f"Menemukan {human_bal:.6f} [bold]{symbol}[/bold]. Melakukan swap ke ETH...")
                    tx_hash = do_swap(symbol, "ETH", balance, mass_mode=True)
                    if tx_hash:
                        wallet_result["tx_hashes"].append(tx_hash)
                    time.sleep(1)
            except Exception as e:
                error(f"Tidak dapat memproses {symbol}: {e}")
        
        success(f"Selesai memproses wallet {A}")
        wallet_result["success"] = True
        
    except Exception as e:
        error(f"Error saat memproses wallet {A}: {e}")
        wallet_result["error"] = str(e)
    
    return wallet_result

def main_auto_all_tasks():
    info("Memulai Mode Otomatis - Semua Wallet & Task (Parallel)")
    
    # Dapatkan semua wallet
    all_wallets = accounts
    all_pks = PK_LIST
    all_proxies = PROXY_LIST
    
    # Kirim notifikasi awal
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send_telegram_message(f"""
🚀 <b>MULAI PROSES BOT</b>

⏰ Waktu Mulai: {start_time}
👥 Total Wallet: {len(all_wallets)}
""")
    
    # Buat thread untuk setiap wallet
    threads = []
    wallet_results = {}
    
    for i, (acct, pk, proxy) in enumerate(zip(all_wallets, all_pks, all_proxies)):
        thread = threading.Thread(
            target=lambda: wallet_results.update({acct.address: process_wallet(acct, pk, proxy, i, len(all_wallets))}),
        )
        threads.append(thread)
        thread.start()
        # Delay kecil antara setiap thread untuk menghindari rate limit
        time.sleep(2)
    
    # Tunggu semua thread selesai
    for thread in threads:
        thread.join()
    
    # Hitung statistik
    total_success = sum(1 for r in wallet_results.values() if r["success"])
    total_failed = len(wallet_results) - total_success
    total_tx = sum(len(r.get("tx_hashes", [])) for r in wallet_results.values())
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Kirim rekap hasil ke Telegram
    message = f"""
📊 <b>REKAP HASIL BOT</b>

⏰ Waktu Mulai: {start_time}
⏰ Waktu Selesai: {end_time}
👥 Total Wallet: {len(all_wallets)}
✅ Berhasil: {total_success}
❌ Gagal: {total_failed}
🔗 Total Transaksi: {total_tx}

<b>Detail per Wallet:</b>
"""
    
    for wallet, result in wallet_results.items():
        account_name = get_account_name(wallet)
        status = "✅ Berhasil" if result["success"] else f"❌ Gagal: {result['error']}"
        message += f"""
👛 Account: <b>{account_name}</b>
📝 Wallet: <code>{wallet}</code>
📊 Status: {status}
"""
        if result.get("tx_hashes"):
            message += "🔗 Tx Hashes:\n"
            for tx in result["tx_hashes"]:
                message += f"<code>{tx}</code>\n"
        message += "➖➖➖➖➖➖➖➖➖➖\n"
    
    send_telegram_message(message)
    info("Semua wallet telah selesai diproses!")

@retry_on_failure
def do_swap(src_sym, dst_sym, amt, mass_mode=False):
    src, dst = TOKENS[src_sym], TOKENS[dst_sym]
    deadline = int(time.time()) + 120
    if not mass_mode: info(f"Mempersiapkan swap {w3.from_wei(amt, 'ether')} {src_sym} -> {dst_sym}")
    
    # Special handling for ETH -> WETH
    if src_sym == "ETH" and dst_sym == "WETH":
        try:
            weth_contract = w3.eth.contract(address=WETH_ADDR, abi=WETH_DEPOSIT_ABI)
            tx_params = {
                'from': A,
                'value': amt,
                'nonce': w3.eth.get_transaction_count(A),
                'gas': GAS_SW,
                'gasPrice': GAS_P
            }
            tx = weth_contract.functions.deposit().build_transaction(tx_params)
            if not chk_native(tx['gas'] * tx['gasPrice'] + tx.get('value', 0)):
                return None
            sig = w3.eth.account.sign_transaction(tx, PK)
            tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
            rec = wait_for_tx(tx_hash, f"Mengirim deposit ETH -> WETH...")
            if rec and rec.status == 1:
                success(f"Deposit ETH -> WETH berhasil! 🎉 Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
                return tx_hash.hex()
            else:
                error(f"Deposit ETH -> WETH gagal! ❌ Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
                return None
        except Exception as e:
            error(f"Error during ETH -> WETH deposit: {e}")
            return None
    
    # Handle other swaps
    paths, chosen_path, amount_out = [], None, None
    
    if dst_sym == "ETH":
        paths = [[src['address'], WETH_ADDR]]
    elif src['address'] and dst['address']:
        paths = [[src['address'], WETH_ADDR, dst['address']], [src['address'], dst['address']]]
    else:
        paths = [[src['address'], WETH_ADDR]] if src['address'] else [[WETH_ADDR, dst['address']]]
    
    for p in paths:
        try:
            amounts = router.functions.getAmountsOut(amt, p).call()
            amount_out, chosen_path = amounts[-1], p
            break
        except Exception as e:
            if not mass_mode:
                error(f"Error calculating amounts for path {p}: {e}")
            continue
            
    if amount_out is None:
        if not mass_mode: error("Tidak dapat menemukan pool likuid untuk swap ini.")
        return None
        
    min_out = int(amount_out * (1 - SLIPPAGE))
    
    # Handle approvals
    if src_sym != "ETH" and not ensure_approve(src['address'], amt):
        return None
        
    tx_params = {
        'from': A,
        'nonce': w3.eth.get_transaction_count(A),
        'gas': GAS_SW,
        'gasPrice': GAS_P
    }
    
    try:
        if src_sym == "ETH":
            fn = router.functions.swapExactETHForTokens(min_out, chosen_path, A, deadline)
            tx_params['value'] = amt
        elif dst_sym == "ETH":
            fn = router.functions.swapExactTokensForETH(amt, min_out, chosen_path, A, deadline)
        else:
            fn = router.functions.swapExactTokensForTokens(amt, min_out, chosen_path, A, deadline)
            
        tx = fn.build_transaction(tx_params)
        if not chk_native(tx['gas'] * tx['gasPrice'] + tx.get('value', 0)):
            return None
            
        sig = w3.eth.account.sign_transaction(tx, PK)
        tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
        rec = wait_for_tx(tx_hash, f"Mengirim swap {src_sym} -> {dst_sym}...")
        
        if rec and rec.status == 1:
            success(f"Swap {src_sym} -> {dst_sym} berhasil! 🎉 Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
            return tx_hash.hex()
        else:
            error(f"Swap {src_sym} -> {dst_sym} gagal! ❌ Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
            return None
            
    except Exception as e:
        error(f"Error during swap {src_sym} -> {dst_sym}: {e}")
        return None

@retry_on_failure
def add_liquidity(token_sym, eth_wei):
    """Menambahkan likuiditas ke pool."""
    if token_sym not in TOKENS:
        raise ValueError(f"Token {token_sym} tidak ditemukan")
    
    token_addr = TOKENS[token_sym]["address"]
    if token_addr == WETH_ADDR:
        raise ValueError("Tidak dapat menambahkan likuiditas ETH/WETH - gunakan token lain")
    
    # Validasi jumlah minimum ETH
    MIN_ETH = w3.to_wei(0.001, 'ether')  # Minimum 0.001 ETH
    if eth_wei < MIN_ETH:
        raise ValueError(f"Jumlah ETH terlalu kecil. Minimum: {w3.from_wei(MIN_ETH, 'ether')} ETH")
    
    info(f"Mencoba menambah likuiditas untuk {w3.from_wei(eth_wei, 'ether')} ETH dan {token_sym}...")
    
    try:
        # Get token contract
        token_contract = w3.eth.contract(address=token_addr, abi=ERC20_ABI)
        
        # Calculate token amount based on current price
        token_balance = token_contract.functions.balanceOf(A).call()
        if token_balance == 0:
            raise ValueError(f"Tidak memiliki token {token_sym}")
            
        info(f"Saldo token {token_sym}: {w3.from_wei(token_balance, 'ether')}")
        
        # Validasi jumlah minimum token
        MIN_TOKEN = w3.to_wei(0.001, 'ether')  # Minimum 0.001 token
        if token_balance < MIN_TOKEN:
            raise ValueError(f"Jumlah token terlalu kecil. Minimum: {w3.from_wei(MIN_TOKEN, 'ether')} {token_sym}")
        
        # Ensure token is approved
        if not ensure_approve(token_addr, token_balance):
            return None
            
        # Calculate minimum amounts with slippage
        token_min = int(token_balance * (1 - SLIPPAGE))
        eth_min = int(eth_wei * (1 - SLIPPAGE))
        
        info(f"Minimum token: {w3.from_wei(token_min, 'ether')} {token_sym}")
        info(f"Minimum ETH: {w3.from_wei(eth_min, 'ether')} ETH")
        
        # Add liquidity
        deadline = int(time.time()) + 300  # 5 minutes
        tx = router.functions.addLiquidityETH(
            token_addr,
            token_balance,
            token_min,  # Use calculated minimum
            eth_min,    # Use calculated minimum
            A,
            deadline
        ).build_transaction({
            'from': A,
            'value': eth_wei,
            'gas': GAS_SW,  # Use swap gas limit instead of approval
            'gasPrice': GAS_P,
            'nonce': w3.eth.get_transaction_count(A)
        })
        
        if not chk_native(tx['gas'] * tx['gasPrice'] + tx.get('value', 0)):
            return None
            
        sig = w3.eth.account.sign_transaction(tx, PK)
        tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
        
        rec = wait_for_tx(tx_hash, "Menunggu konfirmasi penambahan likuiditas...")
        if rec and rec.status == 1:
            success(f"✅ Likuiditas berhasil ditambahkan! Tx: {tx_hash.hex()}")
            return tx_hash.hex()
        else:
            error(f"❌ Gagal menambahkan likuiditas. Status: {rec.status if rec else 'No receipt'}")
            if rec and rec.status == 0:
                error("Transaksi gagal di level smart contract. Mungkin jumlah terlalu kecil atau pool belum ada.")
            return None
            
    except Exception as e:
        error(f"Error saat menambahkan likuiditas: {str(e)}")
        return None

@retry_on_failure
def ensure_approve(token_addr, amt):
    if token_addr is None: return True
    c = w3.eth.contract(address=token_addr, abi=ERC20_ABI)
    alw = c.functions.allowance(A, ROUTER_ADDR).call()
    if alw < amt:
        info(f"Mengirim transaksi approve untuk token...")
        tx = c.functions.approve(ROUTER_ADDR, 2**256 - 1).build_transaction({'from': A, 'nonce': w3.eth.get_transaction_count(A), 'gas': GAS_AP, 'gasPrice': GAS_P, 'chainId': CHAIN})
        if not chk_native(tx['gas'] * tx['gasPrice']): return False
        sig = w3.eth.account.sign_transaction(tx, PK); tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
        rec = wait_for_tx(tx_hash, "Menunggu konfirmasi approve...")
        if rec and rec.status == 1: success(f"Approve berhasil: [yellow]{tx_hash.hex()}[/yellow]"); return True
        else: error(f"Approve gagal: [yellow]{tx_hash.hex()}[/yellow]"); return False
    return True

def display_main_menu():
    mass_swap_state = "[bold green]ON[/bold green]" if mass_swap_enabled else "[bold red]OFF[/bold red]"
    menu_text = f"""
[yellow]1.[/yellow] [white]Swap Manual[/white]
[yellow]2.[/yellow] [white]Swap SEMUA Token ke ETH[/white]
[yellow]3.[/yellow] [white]Tambah Likuiditas (Pasangan ETH)[/white]
[yellow]4.[/yellow] [white]Toggle Mode Mass Swap (Saat ini: {mass_swap_state})[/white]
[yellow]5.[/yellow] [white]Mode Otomatis - Semua Wallet & Task[/white]
[yellow]6.[/yellow] [white]Keluar[/white]
"""
    console.print(Panel(menu_text, title="[bold]PILIH AKSI[/bold]", border_style="cyan", expand=False))

def main_add_liquidity():
    global A, PK, PROXY
    info("Memulai Tambah Likuiditas (Pasangan ETH)...")
    
    # Pilih token
    while True:
        token_sym = select_token_from_list(
            "Pilih Token yang Akan Dipasangkan dengan ETH",
            exclude_symbols=['ETH', 'WETH']
        )
        if token_sym is None: 
            info("Operasi tambah likuiditas dibatalkan.")
            return
        break
    
    # Input jumlah ETH dengan validasi
    while True:
        try:
            eth_amt_str = prompt(f"Jumlah ETH yang akan ditambahkan untuk pasangan {token_sym} (minimal 0.001 ETH): ").strip()
            eth_wei = w3.to_wei(float(eth_amt_str), 'ether')
            
            # Validasi minimum ETH
            MIN_ETH = w3.to_wei(0.001, 'ether')
            if eth_wei < MIN_ETH:
                error(f"Jumlah ETH terlalu kecil. Minimum: {w3.from_wei(MIN_ETH, 'ether')} ETH")
                continue
                
            break
        except ValueError:
            error("Jumlah ETH tidak valid. Masukkan angka yang valid.")
            continue
    
    # Pilih wallet
    selected_wallets, selected_pks, selected_proxies = select_wallets()
    
    # Proses setiap wallet
    for i, (acct, pk, proxy) in enumerate(zip(selected_wallets, selected_pks, selected_proxies)):
        A, PK, PROXY = acct.address, pk, proxy
        console.print(Rule(f"Memproses Dompet {i+1}/{len(selected_wallets)}: {A}", style="bold green"))
        
        # Cek saldo token
        token_contract = w3.eth.contract(address=TOKENS[token_sym]["address"], abi=ERC20_ABI)
        token_balance = token_contract.functions.balanceOf(A).call()
        token_decimals = TOKENS[token_sym].get('decimals', 18)
        
        # Convert to human readable format
        human_balance = token_balance / (10 ** token_decimals)
        MIN_TOKEN = 0.001  # Minimum in human readable format
        
        info(f"Saldo {token_sym}: {human_balance}")
        info(f"Minimum yang dibutuhkan: {MIN_TOKEN} {token_sym}")
        
        if human_balance < MIN_TOKEN:
            error(f"Saldo {token_sym} tidak cukup. Minimum: {MIN_TOKEN} {token_sym}")
            continue
            
        # Coba tambah likuiditas
        tx_hash = add_liquidity(token_sym, eth_wei)
        if tx_hash:
            success(f"Berhasil menambahkan likuiditas untuk wallet {A}")
        else:
            error(f"Gagal menambahkan likuiditas untuk wallet {A}")

def main_swap_all_to_eth():
    global A, PK, PROXY
    info("Memulai Swap SEMUA Token ke ETH...")
    selected_wallets, selected_pks, selected_proxies = select_wallets()
    for i, (acct, pk, proxy) in enumerate(zip(selected_wallets, selected_pks, selected_proxies)):
        A, PK, PROXY = acct.address, pk, proxy
        console.print(Rule(f"Memproses Dompet {i+1}/{len(selected_wallets)}: {A}", style="bold green"))
        for symbol, token_data in TOKENS.items():
            if symbol in ["ETH", "WETH"] or not token_data.get("address"): continue
            try:
                contract = w3.eth.contract(address=token_data["address"], abi=ERC20_ABI)
                balance = contract.functions.balanceOf(A).call()
                if balance > 0:
                    human_bal = balance / (10**token_data.get('decimals', 18))
                    info(f"Menemukan {human_bal:.6f} [bold]{symbol}[/bold]. Melakukan swap ke ETH...")
                    do_swap(symbol, "ETH", balance, mass_mode=True)
                    time.sleep(2)
            except Exception as e: error(f"Tidak dapat memproses {symbol}: {e}")

def main_toggle_mass_swap():
    global mass_swap_enabled
    mass_swap_enabled = not mass_swap_enabled
    state = "[bold green]ON[/bold green]" if mass_swap_enabled else "[bold red]OFF[/bold red]"
    success(f"Mode Mass Swap sekarang {state}")
    warning("Mode Mass Swap belum diimplementasikan di versi ini.")

def main_manual_swap():
    global A, PK, PROXY
    info("Memulai Swap Manual...")
    s = select_token_from_list("Pilih Token Sumber (FROM)")
    if s is None: info("Swap dibatalkan."); return
    d = select_token_from_list("Pilih Token Tujuan (TO)", exclude_symbols=[s])
    if d is None: info("Swap dibatalkan."); return
    try:
        raw_amt = float(prompt(f"Jumlah {s} yang akan di-swap: ").strip())
        repeat = int(prompt("Ulangi berapa kali? (default 1): ") or 1)
        delay = float(prompt("Jeda antar swap (detik, default 1): ") or 1)
        amount_wei = int(raw_amt * (10 ** TOKENS[s]['decimals']))
    except ValueError: error("Input numerik tidak valid."); return
    selected_wallets, selected_pks, selected_proxies = select_wallets()
    for i, (acct, pk, proxy) in enumerate(zip(selected_wallets, selected_pks, selected_proxies)):
        A, PK, PROXY = acct.address, pk, proxy
        console.print(Rule(f"Memproses Dompet {i+1}/{len(selected_wallets)}: {A}", style="bold green"))
        for j in range(repeat):
            info(f"Eksekusi swap #{j+1}/{repeat}...")
            do_swap(s, d, amount_wei)
            if j < repeat - 1: info(f"Menunggu {delay} detik..."); time.sleep(delay)

def main():
    fetch_and_load_tokens()
    while True:
        clear_screen()
        console.print(Rule("[bold magenta]Mega Testnet Trading Bot v2.2 (Task Mode)[/bold magenta]"))
        display_wallet_summary()
        display_main_menu()
        choice = prompt("Masukkan pilihan Anda (1-6): ")
        
        actions = {
            '1': main_manual_swap,
            '2': main_swap_all_to_eth,
            '3': main_add_liquidity,
            '4': main_toggle_mass_swap,
            '5': main_auto_all_tasks,
        }

        if choice in actions:
            actions[choice]()
        elif choice == '6':
            info("Keluar dari bot. Sampai jumpa!")
            break
        else:
            error("Pilihan tidak valid, silakan coba lagi.")
        
        if choice != '6':
            prompt("\nOperasi selesai. Tekan Enter untuk kembali ke menu utama...")

if __name__ == "__main__":
    main()