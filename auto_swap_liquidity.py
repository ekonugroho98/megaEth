#!/usr/bin/env python3
"""
Automated Swap and Liquidity Bot for Mega Testnet
Script ini akan melakukan swap dan tambah likuiditas secara otomatis
"""

import json
import os
import time
import requests
import random
from dotenv import load_dotenv
from web3 import Web3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
import web3

console = Console()

def info(msg): console.print(f"[bold cyan][*][/bold cyan] {msg}")
def success(msg): console.print(f"[bold green][+][/bold green] {msg}")
def error(msg): console.print(f"[bold red][!][/bold red] {msg}")
def warning(msg): console.print(f"[bold yellow][-][/bold yellow] {msg}")

def load_proxies(filename="proxies.txt"):
    """Memuat semua proxy dari file."""
    proxies = []
    try:
        with open(filename, "r") as f:
            for line in f:
                proxy_str = line.strip()
                if proxy_str:
                    proxy_url = f"http://{proxy_str}"
                    proxies.append({"http": proxy_url, "https": proxy_url})
        if proxies:
            info(f"Berhasil memuat {len(proxies)} proxy dari {filename}")
    except FileNotFoundError:
        info(f"File {filename} tidak ditemukan, menjalankan tanpa proxy")
    return proxies

# Load proxies
PROXIES = load_proxies()

def get_proxy_for_wallet(wallet_index):
    """Mendapatkan proxy untuk wallet tertentu."""
    if not PROXIES:
        return None
    # Rotasi proxy berdasarkan indeks wallet
    proxy_index = wallet_index % len(PROXIES)
    return PROXIES[proxy_index]

def create_web3_with_proxy(proxy=None):
    """Membuat instance Web3 dengan proxy tertentu."""
    request_kwargs = {"proxies": proxy} if proxy else {}
    return Web3(Web3.HTTPProvider(RPC, request_kwargs=request_kwargs))

def wait_for_tx(w3_instance, tx_hash, message):
    with console.status(f"[bold green]{message} [dim]{tx_hash.hex()}[/dim][/bold green]", spinner="dots") as status:
        try:
            receipt = w3_instance.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            return receipt
        except Exception as e:
            error(f"Timeout atau error saat menunggu transaksi: {e}")
            return None

# Konfigurasi RPC dan Chain
RPC = 'https://carrot.megaeth.com/rpc'
CHAIN = 6342

# Buat Web3 instance default (tanpa proxy untuk koneksi awal)
w3 = create_web3_with_proxy()

def load_private_keys():
    pk_list = []
    try:
        with open("private_keys.txt", "r") as f:
            keys = [line.strip() for line in f if line.strip()]
            if keys:
                info("Memuat private key dari [bold]private_keys.txt[/bold]")
                pk_list.extend(keys)
    except FileNotFoundError:
        pass
    if not pk_list:
        warning("private_keys.txt tidak ditemukan atau kosong. Mencoba dari environment variables.")
        load_dotenv()
        raw_keys = os.getenv("PRIVATE_KEYS") or ""
        single_key = os.getenv("PRIVATE_KEY") or ""
        if raw_keys: pk_list.extend([k.strip() for k in raw_keys.split(",") if k.strip()])
        if single_key and single_key not in pk_list: pk_list.append(single_key)
        if pk_list: info("Memuat private key dari environment variables.")
    if not pk_list:
        error("Tidak ada private key yang ditemukan. Harap sediakan di `private_keys.txt` atau di environment variables.")
        exit()
    return pk_list

PK_LIST = load_private_keys()
accounts = [w3.eth.account.from_key(pk) for pk in PK_LIST]

# ABI Definitions
PAIR_ABI = json.loads("""[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"}]""")
FACTORY_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"}],"name":"getPair","outputs":[{"name":"pair","type":"address"}],"stateMutability":"view","type":"function"}]""")
ERC20_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"}]""")
ROUTER_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"amountIn","type":"uint256"},{"name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"name":"","type":"uint256[]"}],"type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"WETH","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amountTokenDesired","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"payable","type":"function"}]""")

# Konfigurasi
ROUTER_ADDR = Web3.to_checksum_address("0xa6b579684e943f7d00d616a48cf99b5147fc57a5")
router = w3.eth.contract(address=ROUTER_ADDR, abi=ROUTER_ABI)
WETH_ADDR = router.functions.WETH().call()
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
GAS_P = w3.to_wei('0.001', 'gwei')
GAS_AP, GAS_SW = 200_000, 500_000
SLIPPAGE = 0.11
TOKENS = {}

info("Menyambungkan ke RPC...")
if not w3.is_connected(): 
    error("Koneksi RPC gagal!")
    exit()
if w3.eth.chain_id != CHAIN: 
    error(f"Chain ID tidak cocok: diharapkan {CHAIN}, didapat {w3.eth.chain_id}")
    exit()
success("RPC terhubung dengan sukses.")

def fetch_and_load_tokens():
    global TOKENS, router, WETH_ADDR, ZERO_ADDRESS
    router = w3.eth.contract(address=ROUTER_ADDR, abi=ROUTER_ABI)
    WETH_ADDR = router.functions.WETH().call()
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
    
    API_URL = "https://api-testnet.gte.xyz/v1/markets?sortBy=volume&limit=100"
    headers = {
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://testnet.gte.xyz',
        'referer': 'https://testnet.gte.xyz/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
    }
    
    # Gunakan proxy pertama untuk fetch token data
    proxy_to_use = PROXIES[0] if PROXIES else None
    
    with console.status("[bold yellow]Memuat data token...[/bold yellow]", spinner="dots"):
        try:
            resp = requests.get(API_URL, headers=headers, timeout=10, proxies=proxy_to_use)
            resp.raise_for_status()
            markets = resp.json()
            
            if not isinstance(markets, list):
                error("Format data market tidak terduga dari API.")
                return

            for market in markets:
                for token_type in ['baseToken', 'quoteToken']:
                    token_data = market.get(token_type)
                    if token_data:
                        sym = token_data.get("symbol", "").upper().strip()
                        if not sym: continue
                        addr_raw = token_data.get("address", "")
                        if not (isinstance(addr_raw, str) and addr_raw.startswith('0x') and len(addr_raw) == 42):
                            continue
                        if sym not in TOKENS:
                            addr = Web3.to_checksum_address(addr_raw)
                            TOKENS[sym] = {"address": addr, "decimals": token_data.get("decimals", 18)}
            
            TOKENS["ETH"] = {"address": None, "decimals": 18}
            TOKENS["WETH"] = {"address": WETH_ADDR, "decimals": 18}
        except Exception as e: 
            error(f"Gagal memuat data token: {e}")
            exit()
    success(f"Berhasil memuat {len(TOKENS)} token.")

def chk_native(w3_instance, account, need):
    balance = w3_instance.eth.get_balance(account)
    if balance < need: 
        error(f"Saldo ETH tidak cukup. Butuh: {w3_instance.from_wei(need, 'ether')} ETH")
        return False
    return True

def ensure_approve(w3_instance, account, pk, token_addr, amt):
    if token_addr is None: return True
    c = w3_instance.eth.contract(address=token_addr, abi=ERC20_ABI)
    alw = c.functions.allowance(account, ROUTER_ADDR).call()
    if alw < amt:
        info(f"Mengirim transaksi approve untuk token...")
        tx = c.functions.approve(ROUTER_ADDR, 2**256 - 1).build_transaction({
            'from': account, 
            'nonce': w3_instance.eth.get_transaction_count(account), 
            'gas': GAS_AP, 
            'gasPrice': GAS_P, 
            'chainId': CHAIN
        })
        if not chk_native(w3_instance, account, tx['gas'] * tx['gasPrice']): return False
        sig = w3_instance.eth.account.sign_transaction(tx, pk)
        tx_hash = w3_instance.eth.send_raw_transaction(sig.raw_transaction)
        rec = wait_for_tx(w3_instance, tx_hash, "Menunggu konfirmasi approve...")
        if rec and rec.status == 1: 
            success(f"Approve berhasil: [yellow]{tx_hash.hex()}[/yellow]")
            return True
        else: 
            error(f"Approve gagal: [yellow]{tx_hash.hex()}[/yellow]")
            return False
    return True

def do_swap(w3_instance, account, pk, src_sym, dst_sym, amt, mass_mode=False):
    src = TOKENS.get(src_sym)
    dst = TOKENS.get(dst_sym)
    if not src or not dst:
        error(f"Token {src_sym} atau {dst_sym} tidak ditemukan.")
        return False

    deadline = int(time.time()) + 120

    src_addr = src['address'] if src['address'] else WETH_ADDR
    dst_addr = dst['address'] if dst['address'] else WETH_ADDR

    if src_sym == 'ETH' and dst_sym == 'ETH':
        error('Swap ETH ke ETH tidak didukung.')
        return False
    if dst['address'] is None and dst_sym != 'WETH':
        error(f"Token tujuan {dst_sym} tidak memiliki address valid.")
        return False

    if src_addr and dst_addr:
        paths = [[src_addr, dst_addr]]
    elif src_addr:
        paths = [[src_addr, WETH_ADDR]]
    else:
        paths = [[WETH_ADDR, dst_addr]]

    amount_out = None
    chosen_path = None
    
    router_contract = w3_instance.eth.contract(address=ROUTER_ADDR, abi=ROUTER_ABI)
    
    for p in paths:
        if None in p:
            continue
        try:
            amounts = router_contract.functions.getAmountsOut(amt, p).call()
            amount_out, chosen_path = amounts[-1], p
            break
        except Exception as e:
            if not mass_mode:
                error(f"Tidak dapat menemukan pool likuid untuk swap {src_sym} -> {dst_sym}.")
            continue
            
    if amount_out is None:
        if not mass_mode:
            error(f"Tidak dapat menemukan pool likuid untuk swap {src_sym} -> {dst_sym}.")
        return False
        
    min_out = int(amount_out * (1 - SLIPPAGE))
    if not ensure_approve(w3_instance, account, pk, src['address'], amt):
        return False
        
    nonce = w3_instance.eth.get_transaction_count(account)

    tx_params = {'from': account, 'nonce': nonce, 'gas': GAS_SW, 'gasPrice': GAS_P}
    if src_sym == "ETH":
        fn = router_contract.functions.swapExactETHForTokens(min_out, chosen_path, account, deadline)
        tx_params['value'] = amt
    elif dst_sym == "ETH":
        fn = router_contract.functions.swapExactTokensForETH(amt, min_out, chosen_path, account, deadline)
    else:
        fn = router_contract.functions.swapExactTokensForTokens(amt, min_out, chosen_path, account, deadline)

    tx = fn.build_transaction(tx_params)
    if not chk_native(w3_instance, account, tx['gas'] * tx['gasPrice'] + tx.get('value', 0)):
        return False
    sig = w3_instance.eth.account.sign_transaction(tx, pk)
    tx_hash = w3_instance.eth.send_raw_transaction(sig.raw_transaction)
    rec = wait_for_tx(w3_instance, tx_hash, f"Mengirim swap {src_sym} -> {dst_sym}...")
    if rec and rec.status == 1:
        success(f"Swap {src_sym} -> {dst_sym} berhasil! 🎉 Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return True
    else:
        error(f"Swap {src_sym} -> {dst_sym} gagal! ❌ Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return False

def add_liquidity(w3_instance, account, pk, token_sym, eth_wei):
    token_data = TOKENS[token_sym]
    token_addr = token_data['address']
    deadline = int(time.time()) + 120
    
    info(f"Mencoba menambah likuiditas untuk {w3_instance.from_wei(eth_wei, 'ether')} ETH dan {token_sym}...")
    
    router_contract = w3_instance.eth.contract(address=ROUTER_ADDR, abi=ROUTER_ABI)
    
    try:
        _, amounts = router_contract.functions.getAmountsOut(eth_wei, [WETH_ADDR, token_addr]).call()
        token_wei = amounts
    except Exception as e: 
        error(f"Tidak dapat menghitung jumlah token. Mungkin pool belum ada. Error: {e}")
        return False
    
    info(f"Dibutuhkan [bold]{w3_instance.from_wei(token_wei, 'ether')} {token_sym}[/bold] untuk dipasangkan dengan {w3_instance.from_wei(eth_wei, 'ether')} ETH.")
    token_contract = w3_instance.eth.contract(address=token_addr, abi=ERC20_ABI)
    token_balance = token_contract.functions.balanceOf(account).call()
    
    LIQUIDITY_SLIPPAGE = 0.01
    token_min = int(token_wei * (1 - LIQUIDITY_SLIPPAGE))
    eth_min = int(eth_wei * (1 - LIQUIDITY_SLIPPAGE))
    
    if token_balance < token_min:
        error(f"Saldo {token_sym} tidak cukup. Butuh minimal: {w3_instance.from_wei(token_min, 'ether')}, Punya: {w3_instance.from_wei(token_balance, 'ether')}")
        return False
    else:
        if token_balance < token_wei:
            info(f"Saldo cukup dengan toleransi slippage 1%. Menggunakan jumlah yang tersedia.")
            token_wei = token_balance
    
    if not ensure_approve(w3_instance, account, pk, token_addr, token_wei): 
        return False
    
    fn = router_contract.functions.addLiquidityETH(token_addr, token_wei, token_min, eth_min, account, deadline)
    tx_params = {
        'from': account, 
        'value': eth_wei, 
        'nonce': w3_instance.eth.get_transaction_count(account), 
        'gas': GAS_SW, 
        'gasPrice': GAS_P
    }
    tx = fn.build_transaction(tx_params)
    if not chk_native(w3_instance, account, tx['gas'] * tx['gasPrice'] + tx.get('value', 0)): 
        return False
    
    sig = w3_instance.eth.account.sign_transaction(tx, pk)
    tx_hash = w3_instance.eth.send_raw_transaction(sig.raw_transaction)
    rec = wait_for_tx(w3_instance, tx_hash, "Menambah likuiditas...")
    if rec and rec.status == 1: 
        success(f"Likuiditas berhasil ditambah! Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return True
    else: 
        error(f"Gagal menambah likuiditas. Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return False

def automated_swap_and_liquidity():
    """Fungsi utama untuk swap dan tambah likuiditas otomatis"""
    info("Memulai proses otomatis Swap + Add Liquidity...")
    
    # Konfigurasi dari environment variables atau default
    swap_amount_min = float(os.getenv("SWAP_AMOUNT_MIN", "0.0001"))
    swap_amount_max = float(os.getenv("SWAP_AMOUNT_MAX", "0.002"))
    liquidity_amount_min = float(os.getenv("LIQUIDITY_AMOUNT_MIN", "0.0001"))
    liquidity_amount_max = float(os.getenv("LIQUIDITY_AMOUNT_MAX", "0.002"))
    wallet_target = os.getenv("WALLET_TARGET", "all")
    delay_between_wallets = int(os.getenv("DELAY_BETWEEN_WALLETS", "10"))
    delay_between_operations = int(os.getenv("DELAY_BETWEEN_OPERATIONS", "5"))
    
    info(f"Konfigurasi:")
    info(f"  - Jumlah swap: Random antara {swap_amount_min} - {swap_amount_max} ETH")
    info(f"  - Jumlah likuiditas: Random antara {liquidity_amount_min} - {liquidity_amount_max} ETH")
    info(f"  - Target dompet: {wallet_target}")
    info(f"  - Jeda antar dompet: {delay_between_wallets} detik")
    info(f"  - Jeda antar operasi: {delay_between_operations} detik")
    info(f"  - Jumlah proxy tersedia: {len(PROXIES)}")
    
    # Tentukan dompet mana yang akan diproses
    wallets_to_process = []
    if wallet_target.lower() == 'all':
        wallets_to_process = accounts
        info(f"Mode 'all' aktif. Memproses {len(wallets_to_process)} dompet.")
    else:
        try:
            wallet_index = int(wallet_target)
            if wallet_index >= len(accounts):
                error(f"Indeks dompet {wallet_index} tidak valid.")
                return
            wallets_to_process.append(accounts[wallet_index])
        except ValueError:
            error(f"Target dompet '{wallet_target}' tidak valid. Gunakan nomor atau 'all'.")
            return
    
    # Token yang tersedia untuk swap (exclude ETH dan WETH)
    available_tokens = [s for s in TOKENS if s not in ['ETH', 'WETH'] and TOKENS[s].get('address')]
    if not available_tokens:
        error("Tidak ada token yang tersedia untuk swap.")
        return
    
    success_count = 0
    total_wallets = len(wallets_to_process)
    
    for i, wallet in enumerate(wallets_to_process):
        console.print(Rule(f"Memproses dompet {i+1}/{total_wallets}: {wallet.address}", style="bold green"))
        
        # Generate random amounts untuk wallet ini
        random_swap_amount = round(random.uniform(swap_amount_min, swap_amount_max), 6)
        random_liquidity_amount = round(random.uniform(liquidity_amount_min, liquidity_amount_max), 6)
        
        info(f"Wallet ini akan menggunakan:")
        info(f"  - Swap amount: {random_swap_amount} ETH")
        info(f"  - Liquidity amount: {random_liquidity_amount} ETH")
        
        # Dapatkan proxy untuk wallet ini
        wallet_proxy = get_proxy_for_wallet(i)
        if wallet_proxy:
            info(f"Menggunakan proxy untuk wallet ini")
        else:
            info(f"Menjalankan tanpa proxy")
        
        # Buat Web3 instance dengan proxy untuk wallet ini
        w3_wallet = create_web3_with_proxy(wallet_proxy)
        
        # Cek saldo ETH
        eth_balance = w3_wallet.eth.get_balance(wallet.address)
        eth_balance_human = w3_wallet.from_wei(eth_balance, 'ether')
        info(f"Saldo ETH: {eth_balance_human:.6f} ETH")
        
        # Cek apakah saldo cukup untuk operasi
        total_needed = w3_wallet.to_wei(random_swap_amount + random_liquidity_amount, 'ether') + (GAS_SW * GAS_P * 2)
        if eth_balance < total_needed:
            warning(f"Saldo tidak cukup untuk operasi lengkap. Diperlukan minimal {w3_wallet.from_wei(total_needed, 'ether'):.6f} ETH")
            continue
        
        # Langkah 1: Swap ETH ke token random
        random.shuffle(available_tokens)
        swap_successful = False
        successful_token = None
        
        for token_sym in available_tokens:
            info(f"Mencoba swap ETH -> {token_sym}...")
            amount_wei = w3_wallet.to_wei(random_swap_amount, 'ether')
            
            if do_swap(w3_wallet, wallet.address, PK_LIST[accounts.index(wallet)], "ETH", token_sym, amount_wei, mass_mode=True):
                swap_successful = True
                successful_token = token_sym
                break
            else:
                info(f"Swap ke {token_sym} gagal. Mencoba token berikutnya...")
                time.sleep(2)
        
        if not swap_successful:
            error(f"Gagal melakukan swap untuk dompet {wallet.address}")
            continue
        
        # Jeda sebelum add liquidity
        info(f"Menunggu {delay_between_operations} detik sebelum menambah likuiditas...")
        time.sleep(delay_between_operations)
        
        # Langkah 2: Add Liquidity
        info(f"Menambah likuiditas untuk pasangan ETH / {successful_token}...")
        liquidity_eth_wei = w3_wallet.to_wei(random_liquidity_amount, 'ether')
        
        if add_liquidity(w3_wallet, wallet.address, PK_LIST[accounts.index(wallet)], successful_token, liquidity_eth_wei):
            success_count += 1
            success(f"✅ Dompet {wallet.address} berhasil menyelesaikan semua operasi!")
        else:
            error(f"❌ Gagal menambah likuiditas untuk dompet {wallet.address}")
        
        # Jeda antar dompet
        if i < total_wallets - 1:
            info(f"Menunggu {delay_between_wallets} detik sebelum lanjut ke dompet berikutnya...")
            time.sleep(delay_between_wallets)
    
    # Ringkasan hasil
    console.print(Rule("RINGKASAN HASIL", style="bold magenta"))
    success(f"Berhasil memproses {success_count} dari {total_wallets} dompet")
    if success_count < total_wallets:
        warning(f"{total_wallets - success_count} dompet gagal diproses")
    info("Proses otomatis selesai!")

def display_wallet_summary():
    table = Table(title="Ringkasan Dompet", border_style="magenta", show_header=True, header_style="bold cyan")
    table.add_column("Indeks", style="cyan", width=6)
    table.add_column("Alamat Dompet", style="white")
    table.add_column("Saldo ETH", style="green", justify="right")
    for idx, acc in enumerate(accounts):
        try:
            bal_wei = w3.eth.get_balance(acc.address)
            bal_eth = w3.from_wei(bal_wei, 'ether')
            table.add_row(str(idx), acc.address, f"{bal_eth:.6f} ETH")
        except Exception:
            table.add_row(str(idx), acc.address, "[red]Gagal[/red]")
    console.print(table)

def run_continuous_automation():
    """Fungsi untuk menjalankan bot secara kontinyu dengan restart 24 jam"""
    cycle_count = 0
    
    while True:
        cycle_count += 1
        start_time = time.time()
        
        console.print(Rule(f"[bold cyan]Siklus #{cycle_count} - {time.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]", style="cyan"))
        
        try:
            # Jalankan proses otomatis
            automated_swap_and_liquidity()
            
            # Hitung waktu selesai
            end_time = time.time()
            duration = end_time - start_time
            duration_hours = duration / 3600
            
            info(f"Siklus #{cycle_count} selesai dalam {duration_hours:.2f} jam")
            
        except Exception as e:
            error(f"Error dalam siklus #{cycle_count}: {e}")
            import traceback
            error(traceback.format_exc())
        
        # Hitung waktu tunggu untuk siklus berikutnya
        hours_to_wait = 24
        seconds_to_wait = hours_to_wait * 3600
        
        # Kurangi waktu yang sudah terpakai
        actual_wait_time = max(0, seconds_to_wait - duration)
        actual_wait_hours = actual_wait_time / 3600
        
        next_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + actual_wait_time))
        
        console.print(Rule(f"[bold yellow]Menunggu Siklus Berikutnya[/bold yellow]", style="yellow"))
        info(f"Bot akan berjalan lagi dalam {actual_wait_hours:.2f} jam")
        info(f"Jadwal siklus berikutnya: {next_run_time}")
        
        # Tampilkan countdown
        if actual_wait_time > 0:
            with console.status(f"[bold green]Menunggu siklus berikutnya... ({actual_wait_hours:.1f} jam tersisa)[/bold green]", spinner="dots") as status:
                time.sleep(actual_wait_time)
        
        console.print(Rule(f"[bold green]Memulai Siklus #{cycle_count + 1}[/bold green]", style="green"))

if __name__ == "__main__":
    try:
        console.print(Rule("[bold magenta]Automated Swap & Liquidity Bot v1.0 (Multi-Proxy Support + 24h Auto-Restart)[/bold magenta]"))
        
        # Load tokens
        fetch_and_load_tokens()
        
        # Tampilkan ringkasan dompet
        display_wallet_summary()
        
        # Cek apakah mode kontinyu diaktifkan
        continuous_mode = os.getenv("CONTINUOUS_MODE", "false").lower() == 'true'
        
        if continuous_mode:
            info("Mode kontinyu diaktifkan - Bot akan berjalan setiap 24 jam")
            run_continuous_automation()
        else:
            info("Mode sekali jalan - Bot akan berhenti setelah selesai")
            info("Untuk mode kontinyu, set CONTINUOUS_MODE=true di .env")
            # Jalankan proses otomatis sekali
            automated_swap_and_liquidity()
        
    except KeyboardInterrupt:
        info("Proses dihentikan oleh user.")
    except Exception as e:
        error(f"[CRITICAL] Error utama dalam program: {e}")
        import traceback
        error(traceback.format_exc())
        error("Program dihentikan karena error kritis.") 