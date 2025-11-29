# Guía de Despliegue - SATH v1.3 Live Trading

## Pre-requisitos

### En tu servidor Ubuntu:
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose-plugin -y

# Verificar instalación
docker --version
docker compose version
```

---

## Paso 1: Preparar Binance API Keys

### Crear API Key en Binance:
1. Ir a: https://www.binance.com/en/my/settings/api-management
2. Crear nueva API Key
3. **IMPORTANTE - Configurar permisos:**
   - [x] Enable Reading
   - [x] Enable Spot & Margin Trading
   - [ ] Enable Withdrawals (NUNCA habilitar)
   - [ ] Enable Internal Transfer
4. **Restringir por IP:**
   - Agregar la IP de tu servidor Ubuntu
   - Obtener IP del servidor: `curl ifconfig.me`

### Guardar credenciales:
- API Key: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- API Secret: `yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy`

---

## Paso 2: Clonar y Configurar

### Clonar repositorio:
```bash
cd ~
git clone https://github.com/tu-usuario/bot.git sath
cd sath
```

### Crear archivo .env:
```bash
cp .env.production.template .env
nano .env
```

### Editar .env con tus credenciales:
```env
# BINANCE API (PRODUCCIÓN)
BINANCE_API_KEY=tu_api_key_de_binance
BINANCE_API_SECRET=tu_api_secret_de_binance

# DEEPSEEK API
DEEPSEEK_API_KEY=tu_deepseek_api_key

# INFLUXDB (generar tokens seguros)
INFLUXDB_TOKEN=genera_un_token_aleatorio_largo
INFLUXDB_PASSWORD=genera_una_password_segura_aqui
```

**Generar tokens seguros:**
```bash
# Generar token aleatorio
openssl rand -hex 32
```

---

## Paso 3: Verificar Configuración

### Revisar config_live.yaml:
```bash
cat config/config_live.yaml | grep -E "(mode|initial_capital|symbols)"
```

Debe mostrar:
```
mode: "live"
initial_capital: 50
- "BTC/USDT"
- "ETH/USDT"
```

---

## Paso 4: Desplegar con Docker

### Iniciar servicios:
```bash
# Usar docker-compose de producción
docker compose -f docker-compose.live.yml up -d --build
```

### Verificar que está corriendo:
```bash
docker ps

# Salida esperada:
# CONTAINER ID   IMAGE             STATUS          PORTS                    NAMES
# xxxx           bot-trading_bot   Up 5 seconds                             sath_bot_live
# yyyy           influxdb:2.7      Up 10 seconds   0.0.0.0:8086->8086/tcp   sath_influxdb
```

### Ver logs en tiempo real:
```bash
docker logs -f sath_bot_live
```

---

## Paso 5: Verificar Funcionamiento

### Checklist inicial:
```bash
# 1. Verificar conexión a Binance
docker logs sath_bot_live 2>&1 | grep -i "conectado"

# 2. Verificar modo LIVE
docker logs sath_bot_live 2>&1 | grep -i "modo"

# 3. Verificar capital
docker logs sath_bot_live 2>&1 | grep -i "capital"

# 4. Verificar WebSocket
docker logs sath_bot_live 2>&1 | grep -i "websocket"
```

### Ver decisiones de trading:
```bash
# Últimas 50 líneas del log
docker logs sath_bot_live --tail 50

# Filtrar solo decisiones
docker logs sath_bot_live 2>&1 | grep -E "(COMPRA|VENTA|ESPERA)"
```

---

## Comandos Útiles

### Gestión de contenedores:
```bash
# Parar bot
docker compose -f docker-compose.live.yml down

# Reiniciar bot
docker compose -f docker-compose.live.yml restart trading_bot

# Ver uso de recursos
docker stats sath_bot_live

# Ejecutar comando dentro del contenedor
docker exec -it sath_bot_live bash
```

### Logs y monitoreo:
```bash
# Logs últimas 2 horas
docker logs sath_bot_live --since 2h

# Buscar errores
docker logs sath_bot_live 2>&1 | grep -i error

# Contar operaciones
docker logs sath_bot_live 2>&1 | grep -c "EJECUTANDO ORDEN"
```

### InfluxDB:
```bash
# Acceder a InfluxDB UI
# Abrir navegador: http://IP_SERVIDOR:8086
# Usuario: admin
# Password: (el que pusiste en .env)

# Consultar datos desde CLI
docker exec sath_influxdb influx query \
  'from(bucket:"trading_decisions") |> range(start: -1h)' \
  --org trading_bot \
  --token $INFLUXDB_TOKEN
```

---

## Configuración de Seguridad

### Firewall (UFW):
```bash
# Habilitar firewall
sudo ufw enable

# Permitir SSH
sudo ufw allow ssh

# Permitir InfluxDB solo desde localhost
sudo ufw allow from 127.0.0.1 to any port 8086

# Denegar resto
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### Proteger .env:
```bash
# Solo lectura para el usuario
chmod 600 .env
```

---

## Monitoreo Automático (Opcional)

### Crear script de health check:
```bash
cat > ~/check_sath.sh << 'EOF'
#!/bin/bash
if ! docker ps | grep -q sath_bot_live; then
    echo "$(date): Bot no está corriendo, reiniciando..."
    cd ~/sath
    docker compose -f docker-compose.live.yml up -d
fi
EOF
chmod +x ~/check_sath.sh
```

### Agregar a crontab:
```bash
crontab -e
# Agregar línea:
*/5 * * * * ~/check_sath.sh >> ~/sath_health.log 2>&1
```

---

## Troubleshooting

### Error: "Invalid API-key"
- Verificar que la API key esté correcta en .env
- Verificar que la IP del servidor esté en whitelist de Binance
- Verificar que "Spot Trading" esté habilitado

### Error: "Insufficient balance"
- El capital mínimo para operar es ~$11 (mínimo de Binance para BTC)
- Con $50 podrás hacer operaciones pequeñas

### Bot no genera operaciones:
- Es normal, el bot espera condiciones óptimas
- Verificar ATR% > 0.5% (volatilidad mínima)
- Verificar confianza > 60%

### Error de conexión a InfluxDB:
```bash
# Verificar que InfluxDB esté corriendo
docker logs sath_influxdb

# Reiniciar InfluxDB
docker compose -f docker-compose.live.yml restart influxdb
```

---

## Estructura de Riesgo con $50

| Parámetro | Valor | Impacto |
|-----------|-------|---------|
| Capital | $50 | - |
| Max Risk/Trade | 2% | $1 máximo pérdida/operación |
| Kelly Fraction | 0.2 | Position sizing conservador |
| Min Confidence | 60% | Solo trades de alta calidad |
| Kill Switch | 10% | Para bot si pierde $5 |

---

## Checklist Final Pre-Live

- [ ] API Key de Binance creada y restringida por IP
- [ ] .env configurado con todas las credenciales
- [ ] Docker Compose funcionando
- [ ] Logs muestran conexión exitosa
- [ ] WebSocket conectado
- [ ] Capital inicial de $50 depositado en Binance (Spot)
- [ ] Firewall configurado

---

## Contacto y Soporte

Para problemas:
1. Revisar logs: `docker logs sath_bot_live --tail 100`
2. Verificar estado: `docker ps`
3. Revisar .env y configuración
