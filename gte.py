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
def prompt(msg): return console.input(f"[bold yellow]>> {msg}[/bold yellow]")

def load_proxy(filename="proxies.txt"):
    """Memuat satu proxy dari baris pertama file."""
    try:
        with open(filename, "r") as f:
            proxy_str = f.readline().strip()
            if proxy_str:
                proxy_url = f"http://{proxy_str}"
                info(f"Menggunakan proxy: {proxy_str.split('@')[-1]}")
                return {"http": proxy_url, "https": proxy_url}
    except FileNotFoundError:
        pass # Jalan tanpa proxy jika file tidak ada
    return None

PROXY = load_proxy()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def wait_for_tx(tx_hash, message):
    with console.status(f"[bold green]{message} [dim]{tx_hash.hex()}[/dim][/bold green]", spinner="dots") as status:
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            return receipt
        except Exception as e:
            error(f"Timeout atau error saat menunggu transaksi: {e}")
            return None

RPC = 'https://carrot.megaeth.com/rpc'
CHAIN = 6342
w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"proxies": PROXY} if PROXY else {}))

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
mass_swap_enabled = False
A, PK = None, None

PAIR_ABI = json.loads("""[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"}]""")
FACTORY_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"}],"name":"getPair","outputs":[{"name":"pair","type":"address"}],"stateMutability":"view","type":"function"}]""")
ERC20_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"}]""")
ROUTER_ABI = json.loads("""[{"constant":true,"inputs":[{"name":"amountIn","type":"uint256"},{"name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"name":"","type":"uint256[]"}],"type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"WETH","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amountTokenDesired","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"payable","type":"function"}]""")
WETH_DEPOSIT_ABI = [{"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"}]

info("Menyambungkan ke RPC...")
if not w3.is_connected(): error("Koneksi RPC gagal!"); exit()
if w3.eth.chain_id != CHAIN: error(f"Chain ID tidak cocok: diharapkan {CHAIN}, didapat {w3.eth.chain_id}"); exit()
success("RPC terhubung dengan sukses.")

ROUTER_ADDR = Web3.to_checksum_address("0xa6b579684e943f7d00d616a48cf99b5147fc57a5")
router = w3.eth.contract(address=ROUTER_ADDR, abi=ROUTER_ABI)
WETH_ADDR = router.functions.WETH().call()
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
GAS_P = w3.to_wei('0.001', 'gwei')
GAS_AP, GAS_SW = 200_000, 500_000
SLIPPAGE = 0.11
TOKENS = {}

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
    proxy_to_use = PROXY if PROXY else None
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
                        # Validasi address
                        addr_raw = token_data.get("address", "")
                        if not (isinstance(addr_raw, str) and addr_raw.startswith('0x') and len(addr_raw) == 42):
                            continue  # Lewati token dengan address tidak valid
                        # Hanya tambahkan token jika belum ada di daftar
                        if sym not in TOKENS:
                            addr = Web3.to_checksum_address(addr_raw)
                            TOKENS[sym] = {"address": addr, "decimals": token_data.get("decimals", 18)}
            
            TOKENS["ETH"] = {"address": None, "decimals": 18}
            TOKENS["WETH"] = {"address": WETH_ADDR, "decimals": 18}
        except Exception as e: error(f"Gagal memuat data token: {e}"); exit()
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
    sel_accounts = [accounts[i] for i in selected_indices]; sel_pks = [PK_LIST[i] for i in selected_indices]
    addresses = ", ".join(f"[cyan]{acc.address}[/cyan]" for acc in sel_accounts)
    success(f"Dompet terpilih untuk proses ini: {addresses}")
    return sel_accounts, sel_pks

def chk_native(need):
    balance = w3.eth.get_balance(A)
    if balance < need: error(f"Saldo ETH tidak cukup. Butuh: {w3.from_wei(need, 'ether')} ETH"); return False
    return True

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

def do_swap(src_sym, dst_sym, amt, mass_mode=False):
    global A, PK
    if A is None or PK is None:
        error("Wallet belum dipilih. Silakan pilih wallet terlebih dahulu.")
        return False
    
    src = TOKENS.get(src_sym)
    dst = TOKENS.get(dst_sym)
    if not src or not dst:
        error(f"Token {src_sym} atau {dst_sym} tidak ditemukan.")
        return False

    deadline = int(time.time()) + 120

    # --- Perbaikan: Jangan pernah masukkan None ke path ---
    src_addr = src['address'] if src['address'] else WETH_ADDR
    dst_addr = dst['address'] if dst['address'] else WETH_ADDR

    # Jika swap ETH ke ETH, tolak
    if src_sym == 'ETH' and dst_sym == 'ETH':
        error('Swap ETH ke ETH tidak didukung.')
        return False
    # Jika dst['address'] None dan bukan swap ke WETH, tolak
    if dst['address'] is None and dst_sym != 'WETH':
        error(f"Token tujuan {dst_sym} tidak memiliki address valid.")
        return False

    # Path swap
    if src_addr and dst_addr:
        paths = [[src_addr, dst_addr]]
    elif src_addr:
        paths = [[src_addr, WETH_ADDR]]
    else:
        paths = [[WETH_ADDR, dst_addr]]

    amount_out = None
    chosen_path = None
    
    for p in paths:
        # Validasi path tidak mengandung None
        if None in p:
            continue
        try:
            amounts = router.functions.getAmountsOut(amt, p).call()
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
    if not ensure_approve(src['address'], amt):
        return False
    
    if A is None:
        error(f"Variable A (alamat wallet) adalah None! Tidak bisa melakukan swap.")
        return False
        
    nonce = w3.eth.get_transaction_count(A)

    tx_params = {'from': A, 'nonce': nonce, 'gas': GAS_SW, 'gasPrice': GAS_P}
    if src_sym == "ETH":
        fn = router.functions.swapExactETHForTokens(min_out, chosen_path, A, deadline)
        tx_params['value'] = amt
    elif dst_sym == "ETH":
        fn = router.functions.swapExactTokensForETH(amt, min_out, chosen_path, A, deadline)
    else:
        fn = router.functions.swapExactTokensForTokens(amt, min_out, chosen_path, A, deadline)

    tx = fn.build_transaction(tx_params)
    if not chk_native(tx['gas'] * tx['gasPrice'] + tx.get('value', 0)):
        return False
    sig = w3.eth.account.sign_transaction(tx, PK)
    tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
    rec = wait_for_tx(tx_hash, f"Mengirim swap {src_sym} -> {dst_sym}...")
    if rec and rec.status == 1:
        success(f"Swap {src_sym} -> {dst_sym} berhasil! 🎉 Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return True
    else:
        error(f"Swap {src_sym} -> {dst_sym} gagal! ❌ Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
        return False

def add_liquidity(token_sym, eth_wei):
    token_data = TOKENS[token_sym]; token_addr = token_data['address']; deadline = int(time.time()) + 120
    info(f"Mencoba menambah likuiditas untuk {w3.from_wei(eth_wei, 'ether')} ETH dan {token_sym}...")
    try:
        _, amounts = router.functions.getAmountsOut(eth_wei, [WETH_ADDR, token_addr]).call(); token_wei = amounts
    except Exception as e: error(f"Tidak dapat menghitung jumlah token. Mungkin pool belum ada. Error: {e}"); return
    info(f"Dibutuhkan [bold]{w3.from_wei(token_wei, 'ether')} {token_sym}[/bold] untuk dipasangkan dengan {w3.from_wei(eth_wei, 'ether')} ETH.")
    token_contract = w3.eth.contract(address=token_addr, abi=ERC20_ABI); token_balance = token_contract.functions.balanceOf(A).call()
    
    # Periksa saldo dengan toleransi kecil
    if token_balance < token_wei:
        # Coba dengan slippage yang lebih rendah untuk add liquidity
        LIQUIDITY_SLIPPAGE = 0.01  # 1% untuk add liquidity
        token_min = int(token_wei * (1 - LIQUIDITY_SLIPPAGE))
        eth_min = int(eth_wei * (1 - LIQUIDITY_SLIPPAGE))
        
        if token_balance < token_min:
            error(f"Saldo {token_sym} tidak cukup. Butuh minimal: {w3.from_wei(token_min, 'ether')}, Punya: {w3.from_wei(token_balance, 'ether')}")
            return
        else:
            info(f"Saldo cukup dengan toleransi slippage 1%. Menggunakan jumlah yang tersedia.")
            token_wei = token_balance  # Gunakan saldo yang tersedia
    else:
        # Gunakan slippage normal jika saldo cukup
        LIQUIDITY_SLIPPAGE = 0.01  # 1% untuk add liquidity
        token_min = int(token_wei * (1 - LIQUIDITY_SLIPPAGE))
        eth_min = int(eth_wei * (1 - LIQUIDITY_SLIPPAGE))
    
    if not ensure_approve(token_addr, token_wei): return
    fn = router.functions.addLiquidityETH(token_addr, token_wei, token_min, eth_min, A, deadline)
    tx_params = {'from': A, 'value': eth_wei, 'nonce': w3.eth.get_transaction_count(A), 'gas': GAS_SW, 'gasPrice': GAS_P}
    tx = fn.build_transaction(tx_params)
    if not chk_native(tx['gas'] * tx['gasPrice'] + tx.get('value', 0)): return
    sig = w3.eth.account.sign_transaction(tx, PK); tx_hash = w3.eth.send_raw_transaction(sig.raw_transaction)
    rec = wait_for_tx(tx_hash, "Menambah likuiditas...")
    if rec and rec.status == 1: success(f"Likuiditas berhasil ditambah! Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")
    else: error(f"Gagal menambah likuiditas. Tx Hash: [yellow]{tx_hash.hex()}[/yellow]")

def main_manual_swap():
    global A, PK
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
    selected_wallets, selected_pks = select_wallets()
    for i, (acct, pk) in enumerate(zip(selected_wallets, selected_pks)):
        A, PK = acct.address, pk
        console.print(Rule(f"Memproses Dompet {i+1}/{len(selected_wallets)}: {A}", style="bold green"))
        for j in range(repeat):
            info(f"Eksekusi swap #{j+1}/{repeat}...")
            do_swap(s, d, amount_wei)
            if j < repeat - 1: info(f"Menunggu {delay} detik..."); time.sleep(delay)

def main_swap_all_to_eth():
    global A, PK
    info("Memulai Swap SEMUA Token ke ETH...")
    selected_wallets, selected_pks = select_wallets()
    for i, (acct, pk) in enumerate(zip(selected_wallets, selected_pks)):
        A, PK = acct.address, pk
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

def main_add_liquidity():
    global A, PK
    info("Memulai Tambah Likuiditas (Pasangan ETH)...")
    token_sym = select_token_from_list(
        "Pilih Token yang Akan Dipasangkan dengan ETH",
        exclude_symbols=['ETH', 'WETH']
    )
    if token_sym is None: info("Operasi tambah likuiditas dibatalkan."); return
    try:
        eth_amt_str = prompt(f"Jumlah ETH yang akan ditambahkan untuk pasangan {token_sym}: ").strip()
        eth_wei = w3.to_wei(float(eth_amt_str), 'ether')
    except ValueError: error("Jumlah ETH tidak valid."); return
    selected_wallets, selected_pks = select_wallets()
    for i, (acct, pk) in enumerate(zip(selected_wallets, selected_pks)):
        A, PK = acct.address, pk
        console.print(Rule(f"Memproses Dompet {i+1}/{len(selected_wallets)}: {A}", style="bold green"))
        add_liquidity(token_sym, eth_wei)

def main_toggle_mass_swap():
    global mass_swap_enabled
    mass_swap_enabled = not mass_swap_enabled
    state = "[bold green]ON[/bold green]" if mass_swap_enabled else "[bold red]OFF[/bold red]"
    success(f"Mode Mass Swap sekarang {state}")
    warning("Mode Mass Swap belum diimplementasikan di versi ini.")

def main_toggle_proxy():
    global proxy_enabled
    proxy_enabled = not proxy_enabled
    state = "[bold green]ON[/bold green]" if proxy_enabled else "[bold red]OFF[/bold red]"
    success(f"Mode Proxy sekarang {state}")

def main_automated_swap():
    """Fungsi swap dan tambah likuiditas otomatis untuk Docker."""
    info("Menjalankan dalam mode otomatis...")
    try:
        # --- Konfigurasi dari environment variables ---
        swap_amount_env = float(os.getenv("AUTOMATION_SWAP_AMOUNT", "0.0"))
        wallet_target = os.getenv("AUTOMATION_WALLET_TARGET", "all")
        delay_seconds = int(os.getenv("AUTOMATION_DELAY_SECONDS", "10"))
        add_liquidity_enabled = os.getenv('AUTOMATION_ADD_LIQUIDITY', 'true').lower() == 'true'

        # --- Tentukan dompet mana yang akan diproses ---
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
        
        # --- Loop untuk setiap dompet yang dipilih ---
        for i, wallet in enumerate(wallets_to_process):
            console.print(Rule(f"Memproses dompet {i+1}/{len(wallets_to_process)}", style="bold green"))
            
            A, PK = wallet.address, PK_LIST[accounts.index(wallet)]
            
            console.print(Rule(f"Menggunakan dompet: {A}", style="bold green"))

            # Tentukan jumlah swap
            if swap_amount_env > 0.0:
                swap_amount_eth = swap_amount_env
            else:
                swap_amount_eth = random.uniform(0.0001, 0.01)
            
            info(f"Jumlah dasar untuk operasi: {swap_amount_eth:.6f} ETH")

            # --- Langkah 1: Automated Swap ---
            src_sym = "ETH"
            target_tokens = [s for s in TOKENS if s not in ['ETH', 'WETH'] and TOKENS[s].get('address')]
            if not target_tokens:
                error("Tidak ada token tujuan yang tersedia.")
                continue

            random.shuffle(target_tokens)
            
            swap_successful = False
            successful_dst_sym = None
            for dst_sym in target_tokens:
                info(f"Mencoba swap: {src_sym} -> {dst_sym}")
                amount_wei = w3.to_wei(swap_amount_eth, 'ether')
                
                if do_swap(src_sym, dst_sym, amount_wei, mass_mode=True):
                    swap_successful = True
                    successful_dst_sym = dst_sym
                    break
                else:
                    info(f"Swap ke {dst_sym} tidak berhasil. Mencoba token berikutnya...")
                    time.sleep(2)

            # --- Langkah 2: Automated Add Liquidity (jika swap berhasil) ---
            if swap_successful and add_liquidity_enabled:
                info(f"Swap berhasil. Menunggu 5 detik sebelum menambah likuiditas...")
                time.sleep(5)
                
                info(f"Menambah likuiditas untuk pasangan ETH / {successful_dst_sym}...")
                liquidity_eth_wei = w3.to_wei(swap_amount_eth, 'ether')
                add_liquidity(successful_dst_sym, liquidity_eth_wei)

            elif not swap_successful:
                error(f"Gagal menemukan token yang bisa di-swap untuk dompet {A}.")

            # Jeda antar dompet
            if len(wallets_to_process) > 1 and i < len(wallets_to_process) - 1:
                info(f"Menunggu {delay_seconds} detik sebelum lanjut ke dompet berikutnya...")
                time.sleep(delay_seconds)

    except Exception as e:
        error(f"Terjadi error dalam mode otomatis: {e}")
    finally:
        info("Operasi otomatis selesai.")

def display_wallet_summary():
    table = Table(title="Ringkasan Dompet", border_style="magenta", show_header=True, header_style="bold cyan")
    table.add_column("Indeks", style="cyan", width=6)
    table.add_column("Alamat Dompet", style="white")
    table.add_column("Saldo ETH", style="green", justify="right")
    for idx, acc in enumerate(accounts):
        try:
            bal_wei = w3.eth.get_balance(acc.address); bal_eth = w3.from_wei(bal_wei, 'ether')
            table.add_row(str(idx), acc.address, f"{bal_eth:.6f} ETH")
        except Exception:
            table.add_row(str(idx), acc.address, "[red]Gagal[/red]")
    console.print(table)

def display_main_menu():
    mass_swap_state = "[bold green]ON[/bold green]" if mass_swap_enabled else "[bold red]OFF[/bold red]"
    menu_text = f"""
[yellow]1.[/yellow] [white]Swap Manual[/white]
[yellow]2.[/yellow] [white]Swap SEMUA Token ke ETH[/white]
[yellow]3.[/yellow] [white]Tambah Likuiditas (Pasangan ETH)[/white]
[yellow]4.[/yellow] [white]Toggle Mode Mass Swap (Saat ini: {mass_swap_state})[/white]
[yellow]5.[/yellow] [white]Keluar[/white]
"""
    console.print(Panel(menu_text, title="[bold]PILIH AKSI[/bold]", border_style="cyan", expand=False))

if __name__ == "__main__":
    try:
        fetch_and_load_tokens()

        # Periksa apakah mode otomatis diaktifkan
        if os.getenv('AUTOMATION_MODE', 'false').lower() == 'true':
            main_automated_swap()
        else:
            # Jalankan loop interaktif seperti biasa
            while True:
                clear_screen()
                console.print(Rule("[bold magenta]Mega Testnet Trading Bot v2.3 (Proxy Enabled)[/bold magenta]"))
                display_wallet_summary()
                display_main_menu()
                choice = prompt("Masukkan pilihan Anda (1-5): ")
                
                actions = {
                    '1': main_manual_swap,
                    '2': main_swap_all_to_eth,
                    '3': main_add_liquidity,
                    '4': main_toggle_proxy,
                }

                if choice in actions:
                    actions[choice]()
                elif choice == '5':
                    info("Keluar dari bot. Sampai jumpa!")
                    break
                else:
                    error("Pilihan tidak valid, silakan coba lagi.")
                
                if choice != '5':
                    prompt("\nOperasi selesai. Tekan Enter untuk kembali ke menu utama...")
    except Exception as e:
        error(f"[CRITICAL] Error utama dalam program: {e}")
        import traceback
        error(traceback.format_exc())
        error("Program dihentikan karena error kritis.")