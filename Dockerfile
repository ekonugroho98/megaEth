# Gunakan base image Python yang ringan
FROM python:3.11-slim

# Tetapkan direktori kerja di dalam container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Salin file requirements.txt terlebih dahulu untuk caching
COPY requirements.txt .

# Instal semua dependensi
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua file proyek ke dalam container
COPY . .

# Buat direktori untuk logs
RUN mkdir -p /app/logs

# Set environment variables untuk Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Perintah yang akan dijalankan saat container dimulai
# Default ke auto_swap_liquidity.py, bisa di-override di docker-compose.yml
CMD ["python3", "auto_swap_liquidity.py"]
