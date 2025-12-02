# ============================================
# SATH Platform API
# ============================================

FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Usuario no-root
RUN useradd -m -u 1000 api && \
    mkdir -p /app/tenants && \
    chown -R api:api /app

USER api

# Puerto
EXPOSE 8000

# Comando
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
