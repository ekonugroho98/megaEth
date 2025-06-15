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
                
        console.print("[bold green]✔️ Konfigurasi dari config.json berhasil dimuat.[/]")
        return config
    except FileNotFoundError:
        console.print("[bold red]❌ Error: File 'config.json' tidak ditemukan. Harap buat file tersebut sesuai contoh.[/]")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print("[bold red]❌ Error: Format file 'config.json' tidak valid. Pastikan format JSON sudah benar.[/]")
        sys.exit(1)

config = load_config()
ANTI_CAPTCHA_KEY = config["ANTI_CAPTCHA_KEY"]

RPC = 'https://carrot.megaeth.com/rpc'
CHAIN = 6342

# Konfigurasi Telegram
TELEGRAM_BOT_TOKEN = "7519988044:AAFXRo2bDE99y46Fl_E_H9vbNNSW23mLvXM"
TELEGRAM_CHAT_ID = "1433257992"

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
    
    with console.status("[bold yellow]Memuat data token...[/bold yellow]", spinner="dots"):
        try:
            resp = requests.get(API_URL, headers=headers, timeout=10)
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
            
        except Exception as e:
            error(f"Gagal memuat data token: {e}")
            # Tetap tambahkan ETH dan WETH meskipun gagal
            TOKENS["ETH"] = {"address": None, "decimals": 18}
            TOKENS["WETH"] = {"address": WETH_ADDR, "decimals": 18}
    
    success(f"Berhasil memuat {len(TOKENS)} token.")

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
    paths, chosen_path, amount_out = [], None, None
    if src['address'] and dst['address']: paths = [[src['address'], WETH_ADDR, dst['address']], [src['address'], dst['address']]]
    elif src['address']: paths = [[src['address'], WETH_ADDR]]
    else: paths = [[WETH_ADDR, dst['address']]]
    for p in paths:
        try:
            amounts = router.functions.getAmountsOut(amt, p).call()
            amount_out, chosen_path = amounts[-1], p
            break
        except Exception: continue
    if amount_out is None:
        if not mass_mode: error("Tidak dapat menemukan pool likuid untuk swap ini.")
        return None
    min_out = int(amount_out * (1 - SLIPPAGE))
    if not ensure_approve(src['address'], amt): return None
    tx_params = {'from': A, 'nonce': w3.eth.get_transaction_count(A), 'gas': GAS_SW, 'gasPrice': GAS_P}
    if src_sym == "ETH": fn = router.functions.swapExactETHForTokens(min_out, chosen_path, A, deadline); tx_params['value'] = amt
    elif dst_sym == "ETH": fn = router.functions.swapExactTokensForETH(amt, min_out, chosen_path, A, deadline)
    else: fn = router.functions.swapExactTokensForTokens(amt, min_out, chosen_path, A, deadline)
    tx = fn.build_transaction(tx_params)
    if not chk_native(tx['gas'] * tx['gasPrice'] + tx.get('value', 0)): return None
    sig = w3.eth.account.sign_transaction(tx, PK); tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
    rec = wait_for_tx(tx_hash, f"Mengirim swap {src_sym} -> {dst_sym}...")
    if rec and rec.status == 1:
        success(f"Swap {src_sym} -> {dst_sym} berhasil! 🎉 Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return tx_hash.hex()
    else:
        error(f"Swap {src_sym} -> {dst_sym} gagal! ❌ Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return None

@retry_on_failure
def add_liquidity(token_sym, eth_wei):
    token_data = TOKENS[token_sym]; token_addr = token_data['address']; deadline = int(time.time()) + 120
    info(f"Mencoba menambah likuiditas untuk {w3.from_wei(eth_wei, 'ether')} ETH dan {token_sym}...")
    try:
        _, amounts = router.functions.getAmountsOut(eth_wei, [WETH_ADDR, token_addr]).call(); token_wei = amounts
    except Exception as e: error(f"Tidak dapat menghitung jumlah token. Mungkin pool belum ada. Error: {e}"); return None
    info(f"Dibutuhkan [bold]{w3.from_wei(token_wei, 'ether')} {token_sym}[/bold] untuk dipasangkan dengan {w3.from_wei(eth_wei, 'ether')} ETH.")
    token_contract = w3.eth.contract(address=token_addr, abi=ERC20_ABI); token_balance = token_contract.functions.balanceOf(A).call()
    if token_balance < token_wei: error(f"Saldo {token_sym} tidak cukup. Butuh: {w3.from_wei(token_wei, 'ether')}, Punya: {w3.from_wei(token_balance, 'ether')}"); return None
    if not ensure_approve(token_addr, token_wei): return None
    token_min = int(token_wei * (1 - SLIPPAGE)); eth_min = int(eth_wei * (1 - SLIPPAGE))
    fn = router.functions.addLiquidityETH(token_addr, token_wei, token_min, eth_min, A, deadline)
    tx_params = {'from': A, 'value': eth_wei, 'nonce': w3.eth.get_transaction_count(A), 'gas': GAS_SW, 'gasPrice': GAS_P}
    tx = fn.build_transaction(tx_params)
    if not chk_native(tx['gas'] * tx['gasPrice'] + tx.get('value', 0)): return None
    sig = w3.eth.account.sign_transaction(tx, PK); tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
    rec = wait_for_tx(tx_hash, "Menambah likuiditas...")
    if rec and rec.status == 1:
        success(f"Likuiditas berhasil ditambah! Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return tx_hash.hex()
    else:
        error(f"Gagal menambah likuiditas. Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
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

def main():
    fetch_and_load_tokens()
    main_auto_all_tasks()

if __name__ == "__main__":
    main()