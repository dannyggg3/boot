# Guía de Despliegue en Ubuntu Server

## Requisitos del Servidor

- **Sistema Operativo**: Ubuntu 22.04 LTS o superior
- **RAM**: Mínimo 2GB (recomendado 4GB)
- **CPU**: 2 cores mínimo
- **Disco**: 20GB mínimo
- **Red**: Conexión estable a internet

## Paso 1: Preparar el Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y git curl wget htop

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install -y docker-compose-plugin

# Verificar instalación
docker --version
docker compose version
```

**Reiniciar sesión para aplicar cambios de grupo:**
```bash
exit
# Reconectar SSH
```

## Paso 2: Clonar el Repositorio

```bash
# Crear directorio de trabajo
mkdir -p ~/trading
cd ~/trading

# Clonar repositorio (reemplazar con tu URL)
git clone https://github.com/tu-usuario/sath-bot.git
cd sath-bot
```

## Paso 3: Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar configuración
nano .env
```

**Contenido del archivo `.env`:**

```env
# ===== APIs de IA =====
DEEPSEEK_API_KEY=sk-tu-clave-deepseek

# ===== Exchange (Binance) =====
BINANCE_API_KEY=tu-api-key
BINANCE_API_SECRET=tu-api-secret

# ===== InfluxDB =====
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=tu-token-seguro-aqui
INFLUXDB_ORG=trading_bot
INFLUXDB_BUCKET=trading_decisions
INFLUXDB_PASSWORD=password-seguro-influxdb

# ===== Grafana (opcional) =====
GRAFANA_PASSWORD=password-seguro-grafana

# ===== Telegram (opcional) =====
TELEGRAM_BOT_TOKEN=tu-token
TELEGRAM_CHAT_ID=tu-chat-id
```

## Paso 4: Configurar el Bot

```bash
# Editar configuración principal
nano config/config.yaml
```

**Configuración recomendada para producción:**

```yaml
# Modo paper para empezar
trading:
  mode: "paper"
  scan_interval: 300  # 5 minutos

# Agentes especializados
ai_agents:
  enabled: true
  min_volatility_percent: 0.5

# Datos avanzados
trading:
  advanced_data:
    enabled: true
    order_book: true
    funding_rate: true
    open_interest: true
```

## Paso 5: Iniciar los Servicios

### Opción A: Solo Bot + InfluxDB

```bash
# Iniciar servicios
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f trading_bot
```

### Opción B: Con Grafana (Monitoreo visual)

```bash
# Iniciar con perfil de monitoreo
docker compose --profile monitoring up -d

# Acceder a Grafana: http://TU_IP:3000
# Usuario: admin
# Password: (el configurado en .env)
```

## Paso 6: Verificar Funcionamiento

```bash
# Ver estado de contenedores
docker compose ps

# Ver logs del bot
docker compose logs trading_bot --tail 100

# Ver logs en tiempo real
docker compose logs -f trading_bot
```

**Logs esperados (v1.3):**

```
Bot iniciado. Presiona Ctrl+C para detener.
🔄 Iniciando análisis PARALELO de 4 símbolos...
=== ANÁLISIS v2 CON AGENTES ESPECIALIZADOS: BTC/USDT ===
📊 Régimen de mercado detectado: TRENDING
🚀 AGENTE DE TENDENCIA activado...
Decisión IA: ESPERA (Confianza: 0.30)
Kelly Sizing: confianza=0.30, risk=1.0%
```

## Paso 7: Monitoreo Continuo

### Ver logs históricos

```bash
# Últimas 500 líneas del log
docker compose exec trading_bot tail -500 /app/logs/trading_bot.log
```

### Acceder a InfluxDB

```bash
# Navegar a: http://TU_IP:8086
# Usuario: admin
# Token: (el configurado en .env)
```

### Reiniciar servicios

```bash
# Reiniciar bot
docker compose restart trading_bot

# Reiniciar todo
docker compose restart
```

### Detener servicios

```bash
# Parar todo
docker compose down

# Parar manteniendo datos
docker compose stop
```

## Paso 8: Actualizar el Bot

```bash
# Obtener última versión
git pull origin main

# Reconstruir imagen
docker compose build --no-cache trading_bot

# Reiniciar con nueva versión
docker compose up -d trading_bot
```

## Seguridad

### Firewall (UFW)

```bash
# Habilitar firewall
sudo ufw enable

# Permitir SSH
sudo ufw allow 22

# Permitir Grafana (opcional, solo si necesitas acceso remoto)
sudo ufw allow 3000

# InfluxDB solo local (no exponer)
# NO ejecutar: ufw allow 8086
```

### SSL/HTTPS (Opcional)

Para acceso seguro a Grafana, considera usar Nginx como proxy inverso con Let's Encrypt.

## Troubleshooting

### El bot no se conecta a Binance

```bash
# Verificar conectividad
docker compose exec trading_bot curl -s https://api.binance.com/api/v3/ping
```

### Error de permisos en logs

```bash
# Dar permisos al directorio
sudo chown -R 1000:1000 ./logs ./data
```

### Container se reinicia constantemente

```bash
# Ver logs de error
docker compose logs trading_bot | grep -i error

# Verificar memoria
free -m
```

### InfluxDB no inicia

```bash
# Verificar volúmenes
docker volume ls

# Reiniciar desde cero (BORRA DATOS)
docker compose down -v
docker compose up -d
```

## Backups

### Backup de datos

```bash
# Crear directorio de backups
mkdir -p ~/backups

# Backup de InfluxDB
docker compose exec influxdb influx backup /tmp/backup
docker cp sath_influxdb:/tmp/backup ~/backups/influxdb_$(date +%Y%m%d)

# Backup de configuración
cp -r config ~/backups/config_$(date +%Y%m%d)
cp .env ~/backups/env_$(date +%Y%m%d)
```

### Restaurar backup

```bash
# Restaurar InfluxDB
docker cp ~/backups/influxdb_YYYYMMDD sath_influxdb:/tmp/restore
docker compose exec influxdb influx restore /tmp/restore
```

## Pasar a Modo LIVE

**IMPORTANTE: Solo después de validar en paper trading por al menos 1-2 semanas.**

1. Editar `config/config.yaml`:
   ```yaml
   trading:
     mode: "live"  # Cambiar de "paper" a "live"
   ```

2. Verificar API keys tienen permisos de trading (no withdrawal)

3. Reiniciar:
   ```bash
   docker compose restart trading_bot
   ```

4. Monitorear constantemente los primeros días

## Soporte

- Logs: `./logs/trading_bot.log`
- Datos: `./data/`
- Configuración: `./config/config.yaml`
- Secretos: `./.env`

---

**Versión**: 1.3
**Última actualización**: 2024
