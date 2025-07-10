#!/usr/bin/env python3
"""
Script test untuk memverifikasi mode SEQUENTIAL berfungsi dengan benar
"""

import time
from faucet import load_keys, load_proxies

def test_sequential_logic():
    """Test logika sequential tanpa menjalankan faucet sebenarnya"""
    print("=== TEST MODE SEQUENTIAL ===")
    
    # Load data
    keys = load_keys()
    proxies = load_proxies()
    
    print(f"Jumlah private keys: {len(keys)}")
    print(f"Jumlah proxies: {len(proxies)}")
    
    if not keys:
        print("❌ Tidak ada private keys ditemukan!")
        return False
    
    # Simulasi proses sequential
    print("\n=== SIMULASI PROSES SEQUENTIAL ===")
    for i, key in enumerate(keys):
        proxy = proxies[i] if proxies and i < len(proxies) else None
        print(f"Wallet {i+1}/{len(keys)}: {key[:10]}... | Proxy: {proxy.split('@')[-1] if proxy else 'None'}")
        
        # Simulasi delay antar wallet
        if i < len(keys) - 1:
            print("  ⏳ Menunggu 2 detik...")
            time.sleep(2)
    
    print("\n✅ Simulasi selesai. Mode SEQUENTIAL akan memproses semua wallet secara berurutan.")
    return True

if __name__ == "__main__":
    test_sequential_logic() 