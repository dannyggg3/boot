# Sistema Autónomo de Trading Híbrido (SATH) v1.2

Bot de trading profesional que combina análisis técnico cuantitativo con razonamiento de IA para trading autónomo en criptomonedas y mercados tradicionales.

## Características Principales

### Core
- **Análisis Híbrido**: Combina indicadores técnicos (RSI, MACD, EMA, Bollinger Bands) con razonamiento de IA
- **Múltiples Proveedores de IA**: Soporte para DeepSeek, OpenAI (GPT-4), y Google Gemini
- **Múltiples Mercados**: Opera en crypto (Binance, Bybit) y mercados tradicionales (acciones/forex vía Interactive Brokers)
- **Gestión de Riesgo Avanzada**: Position sizing automático, stop loss dinámico, kill switch
- **Modos de Operación**: Live, Paper Trading, y Backtesting
- **Configuración Modular**: Todo configurable vía YAML sin tocar código

### Optimizaciones v1.1
- **Análisis Paralelo**: Analiza múltiples símbolos simultáneamente (4x más rápido)
- **Protección Anti-Slippage**: Verificación de precio pre-ejecución y órdenes limit inteligentes

### Inteligencia Avanzada v1.2
- **Agentes Especializados**: Agente de Tendencia y Agente de Reversión con estrategias específicas
- **Filtro de Volatilidad**: No opera en mercados "muertos" (ahorra 70% en API)
- **Datos Avanzados**: Order Book, Funding Rate, Open Interest, Correlaciones
- **Detección de Régimen**: Identifica automáticamente si el mercado está en tendencia, reversión o lateral

## Arquitectura del Sistema

```
┌──────────────────────────────────────────────────────────────────┐
│                     MAIN ORCHESTRATOR (v1.2)                      │
│                ┌─────────────────────────────┐                    │
│                │   ThreadPoolExecutor        │                    │
│                │   (Análisis Paralelo)       │                    │
│                └──────────────┬──────────────┘                    │
└───────────────────────────────┼──────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
     ┌────▼────┐           ┌────▼────┐          ┌────▼────┐
     │ BTC/USDT│           │ ETH/USDT│    ...   │ SOL/USDT│
     └────┬────┘           └────┬────┘          └────┬────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
    ┌───▼────────┐                              ┌───────▼───────┐
    │  MARKET    │                              │   TECHNICAL   │
    │  ENGINE    │                              │   ANALYZER    │
    ├────────────┤                              ├───────────────┤
    │ • OHLCV    │                              │ • RSI, MACD   │
    │ • Order    │                              │ • EMA 50/200  │
    │   Book     │◄─── Datos Avanzados ───►     │ • Bollinger   │
    │ • Funding  │         (v1.2)               │ • ATR         │
    │ • Open Int │                              │ • Volumen     │
    └───────┬────┘                              └───────┬───────┘
            │                                           │
            └─────────────────┬─────────────────────────┘
                              │
    ┌─────────────────────────▼─────────────────────────────────┐
    │                    AI ENGINE (v1.2)                        │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │              DETECTOR DE RÉGIMEN                     │  │
    │  │   ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
    │  │   │ TRENDING │  │ REVERSAL │  │ RANGING/LOW VOL  │  │  │
    │  │   │ RSI 30-70│  │ RSI <30  │  │   (No Opera)     │  │  │
    │  │   │          │  │ RSI >70  │  │                  │  │  │
    │  │   └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │  │
    │  │        │             │                 │            │  │
    │  │        ▼             ▼                 ▼            │  │
    │  │   ┌─────────┐   ┌─────────┐       ┌─────────┐       │  │
    │  │   │ AGENTE  │   │ AGENTE  │       │ ESPERA  │       │  │
    │  │   │TENDENCIA│   │REVERSIÓN│       │(Ahorro) │       │  │
    │  │   └─────────┘   └─────────┘       └─────────┘       │  │
    │  └─────────────────────────────────────────────────────┘  │
    └───────────────────────────┬───────────────────────────────┘
                                │
    ┌───────────────────────────▼───────────────────────────────┐
    │                      RISK MANAGER                          │
    │   ┌─────────────┐  ┌──────────────┐  ┌────────────────┐   │
    │   │ Kill Switch │  │ Position Size│  │ Trailing Stop  │   │
    │   │  (5% loss)  │  │  (2% risk)   │  │    (3%)        │   │
    │   └─────────────┘  └──────────────┘  └────────────────┘   │
    └───────────────────────────┬───────────────────────────────┘
                                │
    ┌───────────────────────────▼───────────────────────────────┐
    │               PROTECCIÓN ANTI-SLIPPAGE (v1.1)              │
    │   ┌──────────────────┐  ┌───────────────────────────┐     │
    │   │ Verificación     │  │ Órdenes Limit Inteligentes│     │
    │   │ Pre-Ejecución    │  │ (Slippage Máx: 0.3%)      │     │
    │   │ (Desvío: 0.5%)   │  │ (Timeout: 30s)            │     │
    │   └──────────────────┘  └───────────────────────────┘     │
    └───────────────────────────────────────────────────────────┘
```

## Requisitos Previos

- Python 3.9 o superior
- Ubuntu Server o cualquier sistema Linux/macOS (Windows con WSL)
- (Opcional) Interactive Brokers TWS o Gateway para trading de acciones/forex

## Instalación

### 1. Clonar el repositorio

```bash
cd /ruta/donde/quieras/el/bot
git clone <tu-repositorio>
cd bot
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Nota**: La librería `ta-lib` puede requerir instalación de dependencias del sistema:

```bash
# Ubuntu/Debian
sudo apt-get install build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# macOS
brew install ta-lib
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
nano .env  # o usa tu editor favorito
```

Rellena tus credenciales en `.env`:

```env
# Ejemplo para DeepSeek
DEEPSEEK_API_KEY=sk-tu-clave-aqui

# Para crypto (Binance)
BINANCE_API_KEY=tu-api-key
BINANCE_API_SECRET=tu-secret
```

### 5. Configurar el bot

Edita `config/config.yaml` según tus preferencias:

```yaml
# Seleccionar proveedor de IA
ai_provider: "deepseek"  # deepseek, openai, gemini

# Seleccionar mercado
market_type: "crypto"  # crypto, forex_stocks

# Símbolos a operar
trading:
  symbols:
    - "BTC/USDT"
    - "ETH/USDT"

  # Modo de operación
  mode: "paper"  # paper, live, backtest
```

## Uso

### Modo Paper Trading (Recomendado para empezar)

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar el bot
python main.py
```

El bot empezará a analizar el mercado y simular operaciones sin usar dinero real.

### Modo Live (Dinero Real)

⚠️ **ADVERTENCIA**: Solo usa este modo cuando hayas probado extensivamente en paper trading.

1. Cambia en `config/config.yaml`:
   ```yaml
   trading:
     mode: "live"
   ```

2. Asegúrate de que tus API keys tienen permisos de trading

3. Ejecuta el bot:
   ```bash
   python main.py
   ```

### Ejecutar como Servicio en Ubuntu Server

Para que el bot corra 24/7:

1. Crea el archivo de servicio:

```bash
sudo nano /etc/systemd/system/tradingbot.service
```

2. Contenido del archivo:

```ini
[Unit]
Description=Trading Bot SATH
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/completa/al/bot
Environment="PATH=/ruta/completa/al/bot/venv/bin"
ExecStart=/ruta/completa/al/bot/venv/bin/python main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

3. Activar y ejecutar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tradingbot
sudo systemctl start tradingbot

# Ver logs
sudo journalctl -u tradingbot -f
```

## Optimizaciones de Rendimiento (v1.1)

### Análisis Paralelo

El bot ahora analiza múltiples símbolos simultáneamente, reduciendo drásticamente el tiempo de escaneo:

```yaml
trading:
  parallel_analysis: true      # Habilitar análisis paralelo
  max_parallel_workers: 4      # Máximo 4 símbolos simultáneos
```

| Símbolos | Modo Secuencial | Modo Paralelo | Mejora |
|----------|-----------------|---------------|--------|
| 2 | ~6s | ~3s | 2x |
| 4 | ~12s | ~3s | 4x |
| 8 | ~24s | ~6s | 4x |

### Protección Anti-Slippage

Evita ejecutar órdenes cuando el precio cambió significativamente desde el análisis:

```yaml
trading:
  price_verification:
    enabled: true
    max_deviation_percent: 0.5   # Abortar si precio cambió >0.5%

  order_execution:
    use_limit_orders: true       # Usar limit en vez de market
    max_slippage_percent: 0.3    # Slippage máximo 0.3%
    limit_order_timeout: 30      # Esperar 30s para que se llene
    on_timeout: "cancel"         # Cancelar si no se llena
```

**Beneficios:**
- ✅ Evita comprar en picos de volatilidad
- ✅ Reduce slippage de ~0.5-1% a ≤0.3%
- ✅ Aborta automáticamente operaciones con precio desfavorable

### Símbolos Optimizados

El bot incluye símbolos preconfigurados por liquidez y volatilidad:

```yaml
trading:
  symbols:
    # TIER 1 - Core (máxima liquidez)
    - "BTC/USDT"    # Patrones técnicos muy respetados
    - "ETH/USDT"    # Segunda más líquida

    # TIER 1 - Extendido (alta volatilidad)
    - "SOL/USDT"    # Excelente para swing trading
    - "XRP/USDT"    # Movimientos direccionales claros
```

## Gestión de Riesgo

El bot incluye múltiples mecanismos de seguridad:

### 1. Position Sizing Automático

Calcula automáticamente el tamaño de cada operación para no arriesgar más del 2% del capital por trade.

### 2. Kill Switch

Si el bot pierde más del 5% del capital total, se apaga automáticamente por 24 horas.

```yaml
security:
  kill_switch:
    enabled: true
    max_loss_percentage: 5.0
    cooldown_period_hours: 24
```

### 3. Trailing Stop Loss

El stop loss sube automáticamente con el precio para asegurar ganancias.

```yaml
risk_management:
  use_trailing_stop: true
  trailing_stop_percentage: 3.0
```

### 4. Drawdown Diario Máximo

Límite de pérdida permitida por día (5% por defecto).

## Configuración Avanzada

### Indicadores Técnicos

Puedes habilitar/deshabilitar indicadores en `config/config.yaml`:

```yaml
technical_analysis:
  indicators:
    rsi:
      enabled: true
      period: 14
      overbought: 70
      oversold: 30

    ema:
      enabled: true
      short_period: 50
      long_period: 200
```

### Notificaciones (Opcional)

Para recibir alertas vía Telegram:

1. Crea un bot con [@BotFather](https://t.me/botfather)
2. Obtén tu Chat ID con [@userinfobot](https://t.me/userinfobot)
3. Configura en `.env`:

```env
TELEGRAM_BOT_TOKEN=tu-token
TELEGRAM_CHAT_ID=tu-chat-id
```

4. Habilita en `config/config.yaml`:

```yaml
notifications:
  telegram:
    enabled: true
```

## Backtesting

Para probar tu estrategia en datos históricos:

```yaml
trading:
  mode: "backtest"

backtesting:
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  initial_capital: 10000
```

## Logs y Monitoreo

Los logs se guardan en `logs/trading_bot.log`.

Ver logs en tiempo real:

```bash
tail -f logs/trading_bot.log
```

Nivel de detalle del log (en `config/config.yaml`):

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Trading de Acciones/Forex con Interactive Brokers

### Requisitos Adicionales

1. Cuenta de Interactive Brokers (puede ser demo)
2. TWS (Trader Workstation) o IB Gateway instalado

### Configuración

1. Descarga IB Gateway: https://www.interactivebrokers.com/en/trading/ibgateway-stable.html

2. Ejecuta IB Gateway y configura:
   - Puerto: 7497 (paper) o 7496 (live)
   - Habilitar API
   - Trusted IP: 127.0.0.1

3. En `config/config.yaml`:

```yaml
market_type: "forex_stocks"

interactive_brokers:
  enabled: true
  host: "127.0.0.1"
  port: 7497  # 7497 = paper, 7496 = live
```

4. Símbolos:

```yaml
trading:
  symbols:
    - "AAPL"      # Acción (Apple)
    - "EURUSD"    # Forex
```

## Estructura del Proyecto

```
bot/
├── config/
│   └── config.yaml           # Configuración principal
├── src/
│   ├── engines/
│   │   ├── ai_engine.py      # Motor de IA (DeepSeek/OpenAI/Gemini)
│   │   └── market_engine.py  # Conexión con exchanges/brokers
│   └── modules/
│       ├── technical_analysis.py  # Indicadores técnicos
│       └── risk_manager.py        # Gestión de riesgo
├── logs/                     # Logs del bot
├── data/                     # Datos de estado y backtests
├── main.py                   # Orquestador principal
├── requirements.txt          # Dependencias
├── .env                      # Credenciales (NO SUBIR A GIT)
└── README.md                 # Esta documentación
```

## Seguridad

🔐 **Credenciales**:
- NUNCA subas el archivo `.env` a GitHub o repositorios públicos
- Usa `.gitignore` para excluir archivos sensibles
- Usa API keys con permisos mínimos (solo trading, no withdrawal)

🛡️ **Mejores Prácticas**:
- Empieza siempre con paper trading
- Usa capital pequeño en las primeras semanas de live trading
- Monitorea los logs diariamente
- Revisa el código antes de ejecutar actualizaciones

## Solución de Problemas

### Error: "No module named 'ccxt'"

```bash
pip install ccxt
```

### Error: "Cannot connect to Interactive Brokers"

1. Verifica que TWS/Gateway está ejecutándose
2. Verifica que el puerto es correcto (7497 o 7496)
3. Verifica que la API está habilitada en TWS

### Error: "Invalid API Key"

Verifica que tus credenciales en `.env` son correctas y tienen permisos de trading.

### El bot no ejecuta operaciones

1. Verifica que el modo no sea `backtest`
2. Revisa los logs para ver si el Risk Manager está rechazando operaciones
3. Verifica que el kill switch no esté activo

## Contribuciones

Este es un proyecto de código abierto. Contribuciones son bienvenidas:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

MIT License - Ver archivo LICENSE

## Disclaimer

⚠️ **ADVERTENCIA LEGAL**:

Este software se proporciona "tal cual" sin garantías de ningún tipo. El trading conlleva riesgos significativos de pérdida de capital. Los desarrolladores no se hacen responsables de pérdidas financieras derivadas del uso de este software.

**Recomendaciones**:
- Nunca operes con dinero que no puedas permitirte perder
- Prueba extensivamente en paper trading antes de usar dinero real
- El rendimiento pasado no garantiza resultados futuros
- Considera consultar con un asesor financiero profesional

## Soporte

Para reportar bugs o solicitar features:
- Abre un issue en GitHub
- Contacta vía email: [tu-email]

## Changelog

### v1.2 (2024)

- **Sistema de Agentes Especializados**:
  - Agente de Tendencia: Opera continuación en retrocesos (RSI 30-70)
  - Agente de Reversión: Opera reversiones en RSI extremos (<30 o >70)
  - Selección automática según régimen de mercado
- **Filtro de Volatilidad Pre-IA**: No invoca API si ATR < 0.5% (ahorra ~70% adicional)
- **Detección de Régimen de Mercado**: trending, reversal, ranging, low_volatility
- **Datos Avanzados de Mercado**:
  - Order Book: Detecta muros de compra/venta, imbalance, spread
  - Funding Rate: Sentimiento del mercado de futuros
  - Open Interest: Dinero entrando/saliendo del mercado
  - Correlaciones: Relación con BTC para altcoins
- **Impacto en Costos de IA**: Reducción adicional del 50-70% por filtro de volatilidad

### v1.1 (2024)

- **Análisis Paralelo**: ThreadPoolExecutor para análisis simultáneo de múltiples símbolos
- **Protección Anti-Slippage**: Verificación de precio pre-ejecución
- **Órdenes Limit Inteligentes**: Conversión automática de market a limit con slippage máximo
- **Símbolos Optimizados**: Configuración tier-based por liquidez y volatilidad
- **Impacto en Costos de IA**: Reducción adicional del 10-20% por ejecución más eficiente

### v1.0 (2024)

- Lanzamiento inicial
- Arquitectura híbrida de IA (ahorro 70-90% en costos de API)
- Soporte multi-exchange (Binance, Bybit, Interactive Brokers)
- Risk Manager con kill switch

---

**Desarrollado con ❤️ para traders algorítmicos**

Versión 1.2 - 2024
