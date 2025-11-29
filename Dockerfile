# ============================================
# SATH - Sistema Autónomo de Trading Híbrido
# Dockerfile para Producción
# ============================================

FROM python:3.11-slim

# Metadata
LABEL maintainer="SATH Trading Bot"
LABEL version="1.3"
LABEL description="Sistema Autónomo de Trading Híbrido con IA"

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV TZ=UTC

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para cache de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar el código fuente
COPY src/ ./src/
COPY main.py .
COPY check_setup.py .

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/data /app/config

# Usuario no-root para seguridad
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app

USER trader

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/logs/trading_bot.log') else 1)"

# Comando por defecto
CMD ["python", "main.py"]
