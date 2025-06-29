# GTE Automation Bot

Bot multifungsi untuk berinteraksi dengan ekosistem GTE (Galactic Trading Empire) di jaringan testnet MegaETH. Proyek ini terdiri dari tiga komponen utama: Bot Trading Manual, Bot Trading Otomatis, dan Bot Faucet Claimer.

## Fitur

### Trading Bot Manual (`gte.py`)
- **Swap Otomatis**: Melakukan swap token secara otomatis.
- **Tambah Likuiditas**: Menambah likuiditas ke pool yang ada.
- **Mode Operasi Ganda**:
    - **Mode Manual/Interaktif**: Memilih token, jumlah, dan dompet secara manual melalui antarmuka terminal.
    - **Mode Otomatis (via Docker)**: Menjalankan swap dan penambahan likuiditas secara otomatis berdasarkan konfigurasi di `docker-compose.yml`.
- **Manajemen Multi-Dompet**: Mendukung penggunaan beberapa dompet secara bersamaan.
- **Dukungan Proxy**: Semua interaksi dengan blockchain dan API dapat diarahkan melalui proxy.

### Trading Bot Otomatis (`auto_swap_liquidity.py`) ⭐ **BARU**
- **Swap + Liquidity Otomatis**: Melakukan swap ETH ke token random dan otomatis menambah likuiditas.
- **Random Amount**: Menggunakan jumlah random untuk menghindari deteksi bot (0.0001 - 0.002 ETH).
- **Multi-Proxy Support**: Setiap wallet menggunakan proxy berbeda untuk load balancing.
- **Anti-Bot Detection**: 
  - Random amounts per wallet
  - Random token selection
  - Proxy rotation
  - Configurable delays
- **Fully Automated**: Tidak memerlukan input manual, berjalan otomatis dari awal sampai selesai.
- **Smart Error Handling**: Skip wallet dengan saldo tidak cukup, retry dengan token berbeda.

### Faucet Claimer (`faucet.py`)
- **Klaim Otomatis**: Mengklaim token testnet dari faucet MegaETH setiap 24 jam.
- **Penyelesaian CAPTCHA**: Terintegrasi dengan layanan Anti-Captcha untuk melewati perlindungan Turnstile.
- **Manajemen Multi-Dompet & Proxy**: Dapat mengklaim untuk beberapa dompet, masing-masing melalui proxy yang berbeda jika dikonfigurasi.

## Prasyarat

- Python 3.10+
- Docker & Docker Compose (untuk metode deployment yang direkomendasikan)
- Akun dan API Key dari [Anti-Captcha](https://anti-captcha.com/) (untuk Faucet Claimer).

## Instalasi dan Konfigurasi

1.  **Clone Repositori**
    ```bash
    git clone <URL_REPOSITORI_ANDA>
    cd <NAMA_DIREKTORI>
    ```

2.  **Buat File Konfigurasi**
    Buat file-file berikut di direktori utama proyek:

    - `private_keys.txt`: Masukkan semua private key dompet Anda, satu per baris.
      ```
      0x...kunci_privat_1
      0x...kunci_privat_2
      ```

    - `proxies.txt` (Opsional): Jika Anda ingin menggunakan proxy, masukkan detailnya dengan format `user:pass@host:port`, satu per baris. Urutan proxy akan sesuai dengan urutan private key.
      ```
      user1:pass1@proxy_host1:port1
      user2:pass2@proxy_host2:port2
      ```

    - `captcha_key.txt`: Masukkan API Key dari Anti-Captcha Anda. File ini hanya diperlukan untuk Faucet Claimer.
      ```
      kunci_api_anti_captcha_anda
      ```

    - `.env` (Opsional): Konfigurasi untuk bot otomatis.
      ```env
      # Random Amount Configuration
      SWAP_AMOUNT_MIN=0.0001
      SWAP_AMOUNT_MAX=0.002
      LIQUIDITY_AMOUNT_MIN=0.0001
      LIQUIDITY_AMOUNT_MAX=0.002
      
      # Wallet Configuration
      WALLET_TARGET=all
      
      # Delay Configuration
      DELAY_BETWEEN_WALLETS=10
      DELAY_BETWEEN_OPERATIONS=5
      ```

3.  **Instal Dependensi (Hanya untuk Penggunaan Manual)**
    Jika Anda ingin menjalankan skrip secara langsung tanpa Docker, instal dependensi Python.
    ```bash
    pip install -r requirements.txt
    ```

## Cara Penggunaan

### 🐳 **Docker Deployment (RECOMMENDED)**

Docker adalah cara terbaik untuk menjalankan bot karena:
- ✅ **Easy Setup**: Tidak perlu install Python dependencies
- ✅ **Auto Restart**: Bot restart otomatis jika crash
- ✅ **Log Management**: Log rotation dan monitoring
- ✅ **Isolation**: Terpisah dari sistem host
- ✅ **24/7 Operation**: Berjalan terus menerus

#### **Quick Start dengan Docker:**

1. **Siapkan file konfigurasi:**
   ```bash
   # Copy example environment file
   cp env.example .env
   
   # Edit konfigurasi sesuai kebutuhan
   nano .env
   ```

2. **Jalankan kedua bot:**
   ```bash
   # Jalankan auto swap bot dan faucet claimer
   docker-compose up -d
   
   # Lihat log real-time
   docker-compose logs -f
   ```

3. **Monitor bot:**
   ```bash
   # Lihat log auto swap bot
   docker-compose logs -f auto-swap-bot
   
   # Lihat log faucet claimer
   docker-compose logs -f faucet-claimer
   
   # Cek status container
   docker-compose ps
   ```

4. **Stop bot:**
   ```bash
   docker-compose down
   ```

#### **Konfigurasi Docker:**

**File `docker-compose.yml` sudah dikonfigurasi dengan:**
- ✅ **Auto Swap Bot**: Berjalan setiap 24 jam secara otomatis
- ✅ **Faucet Claimer**: Klaim faucet setiap 24 jam
- ✅ **Multi-Proxy Support**: Setiap wallet menggunakan proxy berbeda
- ✅ **Random Amounts**: Anti-bot detection
- ✅ **Log Rotation**: Log tidak akan memenuhi disk

**Environment Variables di Docker:**
```yaml
# Auto Swap Bot Configuration
CONTINUOUS_MODE=true              # Mode 24 jam
SWAP_AMOUNT_MIN=0.0001           # Min swap amount
SWAP_AMOUNT_MAX=0.002            # Max swap amount
LIQUIDITY_AMOUNT_MIN=0.0001      # Min liquidity amount
LIQUIDITY_AMOUNT_MAX=0.002       # Max liquidity amount
WALLET_TARGET=all                # Target wallets
DELAY_BETWEEN_WALLETS=10         # Delay between wallets
DELAY_BETWEEN_OPERATIONS=5       # Delay between operations
```

#### **Docker Commands:**

```bash
# Jalankan semua service
docker-compose up -d

# Jalankan hanya auto swap bot
docker-compose up -d auto-swap-bot

# Jalankan hanya faucet claimer
docker-compose up -d faucet-claimer

# Lihat log real-time
docker-compose logs -f

# Restart service
docker-compose restart auto-swap-bot

# Update dan restart
docker-compose down
docker-compose up -d --build

# Cek resource usage
docker stats

# Backup logs
docker-compose logs auto-swap-bot > auto_swap_logs.txt
```

### 🚀 Trading Bot Otomatis (`auto_swap_liquidity.py`) - **RECOMMENDED**

Bot ini adalah versi terbaru yang paling canggih dengan fitur anti-deteksi:

```bash
python3 auto_swap_liquidity.py
```

**Fitur Utama:**
- ✅ **Fully Automated**: Tidak perlu input manual
- ✅ **Random Amounts**: Setiap wallet menggunakan jumlah berbeda (0.0001-0.002 ETH)
- ✅ **Multi-Proxy**: Setiap wallet menggunakan proxy berbeda
- ✅ **Smart Token Selection**: Otomatis pilih token yang bisa di-swap
- ✅ **Error Recovery**: Skip wallet bermasalah, lanjut ke berikutnya
- ✅ **Progress Tracking**: Tampilkan progress dan hasil akhir
- ✅ **24h Auto-Restart**: Berjalan setiap 24 jam secara otomatis

**Konfigurasi via .env:**
```env
# Mode Configuration
CONTINUOUS_MODE=true

# Amount Range (ETH)
SWAP_AMOUNT_MIN=0.0001
SWAP_AMOUNT_MAX=0.002
LIQUIDITY_AMOUNT_MIN=0.0001
LIQUIDITY_AMOUNT_MAX=0.002

# Wallet Selection
WALLET_TARGET=all          # 'all' atau angka indeks (0, 1, 2, dst)

# Delays (seconds)
DELAY_BETWEEN_WALLETS=10   # Jeda antar wallet
DELAY_BETWEEN_OPERATIONS=5 # Jeda antara swap dan liquidity
```

**Contoh Output:**
```
[*] Wallet ini akan menggunakan:
[*]   - Swap amount: 0.001234 ETH
[*]   - Liquidity amount: 0.000876 ETH
[*] Menggunakan proxy untuk wallet ini
[+] Swap ETH -> TOKEN berhasil! 🎉
[+] Likuiditas berhasil ditambah!
✅ Dompet 0x123... berhasil menyelesaikan semua operasi!
```

### Trading Bot Manual (`gte.py`)

#### Penggunaan Manual (Tanpa Docker)

Anda juga bisa menjalankan skrip secara langsung menggunakan Python.

- **Menjalankan Trading Bot:**
  ```bash
  python3 gte.py
  ```
  Skrip akan menampilkan menu interaktif di terminal Anda.

### Faucet Claimer (`faucet.py`)

- **Menjalankan Faucet Claimer:**
  ```bash
  python3 faucet.py
  ```
  Skrip akan mulai mengklaim untuk semua dompet yang terdaftar dan akan berjalan dalam loop 24 jam.

## Struktur Proyek

```
.
├── auto_swap_liquidity.py  # ⭐ Bot Trading Otomatis (BARU)
├── docker-compose.yml      # Mengorkestrasi layanan Docker untuk kedua bot
├── Dockerfile              # Instruksi untuk membangun image Docker
├── faucet.py               # Logika untuk bot Faucet Claimer
├── gte.py                  # Logika untuk bot Trading Manual
├── requirements.txt        # Dependensi Python
├── private_keys.txt        # (Perlu dibuat) Kunci privat dompet
├── proxies.txt             # (Perlu dibuat, opsional) Daftar proxy
├── captcha_key.txt         # (Perlu dibuat) Kunci API Anti-Captcha
└── .env                    # (Perlu dibuat, opsional) Konfigurasi bot otomatis
```

## Perbandingan Bot

| Fitur | `gte.py` | `auto_swap_liquidity.py` |
|-------|----------|--------------------------|
| **Mode Operasi** | Manual/Interactive | Fully Automated |
| **Input Required** | Ya (pilih token, jumlah) | Tidak (semua otomatis) |
| **Random Amounts** | Tidak | ✅ Ya (anti-bot) |
| **Multi-Proxy** | Single proxy | ✅ Rotasi proxy per wallet |
| **Error Handling** | Basic | ✅ Advanced (skip, retry) |
| **Progress Tracking** | Basic | ✅ Detailed |
| **Anti-Bot Features** | Tidak | ✅ Multiple layers |
| **Ease of Use** | Medium | ✅ High |

## Konfigurasi Lanjutan

### Environment Variables untuk `auto_swap_liquidity.py`

```env
# Amount Configuration
SWAP_AMOUNT_MIN=0.0001          # Minimum swap amount (ETH)
SWAP_AMOUNT_MAX=0.002           # Maximum swap amount (ETH)
LIQUIDITY_AMOUNT_MIN=0.0001     # Minimum liquidity amount (ETH)
LIQUIDITY_AMOUNT_MAX=0.002      # Maximum liquidity amount (ETH)

# Wallet Configuration
WALLET_TARGET=all               # 'all' atau indeks wallet (0, 1, 2, dst)

# Timing Configuration
DELAY_BETWEEN_WALLETS=10        # Delay between wallets (seconds)
DELAY_BETWEEN_OPERATIONS=5      # Delay between swap and liquidity (seconds)
```

### Format File Proxy

```
# proxies.txt - Satu proxy per baris
user1:pass1@proxy1.com:8080
user2:pass2@proxy2.com:8080
user3:pass3@proxy3.com:8080
```

### Format File Private Keys

```
# private_keys.txt - Satu private key per baris
0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
```

## Troubleshooting

### Masalah Umum

1. **"Koneksi RPC gagal!"**
   - Periksa koneksi internet
   - Pastikan RPC endpoint aktif
   - Coba gunakan proxy

2. **"Saldo ETH tidak cukup"**
   - Pastikan wallet memiliki ETH untuk gas fee
   - Periksa jumlah yang dikonfigurasi di .env
   - Pastikan saldo > (swap + liquidity + gas)

3. **"Tidak dapat menemukan pool likuid"**
   - Token mungkin tidak memiliki pool
   - Coba token lain atau tunggu beberapa saat
   - Periksa apakah token valid

4. **"Approve gagal"**
   - Periksa gas price dan limit
   - Pastikan wallet memiliki ETH untuk gas
   - Coba lagi setelah beberapa saat

### Log dan Monitoring

```bash
# Lihat log real-time
tail -f auto_swap_liquidity.log

# Monitor transaksi
docker-compose logs -f trading-bot

# Cek status wallet
python3 -c "from auto_swap_liquidity import *; display_wallet_summary()"
```

## Keamanan dan Best Practices

- **Keamanan**: Jangan pernah membagikan file `private_keys.txt` Anda. Pastikan untuk menambahkannya ke `.gitignore` jika belum ada.
- **Testnet**: Semua operasi dilakukan di jaringan testnet MegaETH. Jangan gunakan kunci dari mainnet yang berisi dana nyata.
- **Proxy**: Penggunaan proxy sangat disarankan untuk menghindari pemblokiran IP, terutama saat menjalankan bot untuk banyak akun.
- **Monitoring**: Selalu monitor log dan transaksi untuk memastikan bot berjalan dengan baik.
- **Backup**: Backup private keys dan konfigurasi secara berkala.

## Support

Jika mengalami masalah atau memiliki pertanyaan:
1. Periksa section Troubleshooting di atas
2. Periksa log untuk error messages
3. Pastikan semua file konfigurasi sudah benar
4. Coba jalankan dengan wallet test terlebih dahulu

## Disclaimer

Bot ini dibuat untuk tujuan edukasi dan testing di jaringan testnet. Gunakan dengan bijak dan bertanggung jawab. Penulis tidak bertanggung jawab atas kerugian yang mungkin terjadi. 