# Sistema Autónomo de Trading Híbrido (SATH) v1.5

Bot de trading profesional que combina análisis técnico cuantitativo con razonamiento de IA para trading autónomo en criptomonedas y mercados tradicionales.

**Nuevo en v1.5**: Sistema completo de gestión de posiciones con órdenes OCO reales, supervisión IA, trailing stop inteligente y persistencia SQLite.

## Características Principales

### Core
- **Análisis Híbrido**: Combina indicadores técnicos (RSI, MACD, EMA, Bollinger Bands) con razonamiento de IA
- **Múltiples Proveedores de IA**: Soporte para DeepSeek, OpenAI (GPT-4), y Google Gemini
- **Múltiples Mercados**: Opera en crypto (Binance, Bybit) y mercados tradicionales (acciones/forex vía Interactive Brokers)
- **Gestión de Riesgo Avanzada**: Position sizing automático, stop loss dinámico, kill switch
- **Modos de Operación**: Live, Paper Trading, y Backtesting
- **Configuración Modular**: Todo configurable vía YAML sin tocar código

### Sistema de Gestión de Posiciones v1.5

- **Órdenes OCO Reales**: Stop Loss + Take Profit como orden combinada en el exchange
- **Supervisión IA**: Agente supervisor que analiza posiciones cada 60 segundos
- **Trailing Stop Inteligente**: Se activa automáticamente cuando hay ganancias
- **Persistencia SQLite**: Las posiciones sobreviven reinicios del bot
- **Portfolio Management**: Límite de posiciones concurrentes y exposición máxima
- **Notificaciones**: Alertas Telegram para SL/TP triggers y ajustes IA

### Optimizaciones v1.1-v1.4
- **Análisis Paralelo**: Analiza múltiples símbolos simultáneamente (4x más rápido)
- **Protección Anti-Slippage**: Verificación de precio pre-ejecución y órdenes limit inteligentes
- **Agentes Especializados**: Agente de Tendencia y Agente de Reversión
- **Pre-Filtro Local**: Reduce 50-75% llamadas API
- **Kelly Criterion**: Position sizing dinámico basado en confianza

## Arquitectura del Sistema v1.5

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SATH BOT v1.5                                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     MAIN ORCHESTRATOR                                   │ │
│  │                                                                         │ │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │ │
│  │   │  BTC/USDT    │    │  ETH/USDT    │    │  SOL/USDT    │            │ │
│  │   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘            │ │
│  │          └────────────────────┼────────────────────┘                   │ │
│  └──────────────────────────────┼─────────────────────────────────────────┘ │
│                                  │                                          │
│  ┌───────────────────────────────┴───────────────────────────────────────┐  │
│  │                         ANÁLISIS                                       │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐              ┌─────────────────┐                 │  │
│  │  │  MARKET ENGINE  │              │ TECHNICAL       │                 │  │
│  │  │  • OHLCV        │◄────────────►│ ANALYZER        │                 │  │
│  │  │  • Order Book   │              │ • RSI, MACD     │                 │  │
│  │  │  • Funding Rate │              │ • EMA 50/200    │                 │  │
│  │  └────────┬────────┘              └────────┬────────┘                 │  │
│  │           └────────────────┬───────────────┘                          │  │
│  │                            ▼                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      AI ENGINE                                   │  │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │  │  │
│  │  │  │              DETECTOR DE RÉGIMEN                         │    │  │  │
│  │  │  │   ┌───────────┐  ┌───────────┐  ┌─────────────────┐     │    │  │  │
│  │  │  │   │ TRENDING  │  │ REVERSAL  │  │ RANGING/LOW VOL │     │    │  │  │
│  │  │  │   │  Agente   │  │  Agente   │  │   (No Opera)    │     │    │  │  │
│  │  │  │   │ Tendencia │  │ Reversión │  │                 │     │    │  │  │
│  │  │  │   └─────┬─────┘  └─────┬─────┘  └────────┬────────┘     │    │  │  │
│  │  │  │         └──────────────┼─────────────────┘              │    │  │  │
│  │  │  └────────────────────────┼────────────────────────────────┘    │  │  │
│  │  └───────────────────────────┼─────────────────────────────────────┘  │  │
│  └──────────────────────────────┼────────────────────────────────────────┘  │
│                                 │                                           │
│  ┌──────────────────────────────▼────────────────────────────────────────┐  │
│  │                     RISK MANAGER + KELLY                               │  │
│  │   ┌─────────────┐  ┌───────────────┐  ┌────────────────┐              │  │
│  │   │ Kill Switch │  │Kelly Criterion│  │ Position Sizing │              │  │
│  │   │  (5% loss)  │  │ (Sizing IA)   │  │   (2% risk)     │              │  │
│  │   └─────────────┘  └───────────────┘  └────────────────┘              │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 │                                           │
│                                 ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │              POSITION MANAGEMENT SYSTEM v1.5                          │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │                    POSITION ENGINE                               │ │   │
│  │  │  • Crear posiciones después de orden ejecutada                   │ │   │
│  │  │  • Colocar órdenes de protección (OCO/SL/TP)                    │ │   │
│  │  │  • Monitoreo continuo en background thread                       │ │   │
│  │  │  • Trailing stop automático                                      │ │   │
│  │  │  • Cierre de posiciones y registro de resultados                 │ │   │
│  │  └─────────────────────────┬───────────────────────────────────────┘ │   │
│  │                            │                                         │   │
│  │        ┌───────────────────┼───────────────────┐                     │   │
│  │        ▼                   ▼                   ▼                     │   │
│  │  ┌───────────┐      ┌───────────┐      ┌─────────────┐              │   │
│  │  │  ORDER    │      │ POSITION  │      │  POSITION   │              │   │
│  │  │  MANAGER  │      │   STORE   │      │ SUPERVISOR  │              │   │
│  │  ├───────────┤      ├───────────┤      ├─────────────┤              │   │
│  │  │ • OCO     │      │ • SQLite  │      │ • IA cada   │              │   │
│  │  │ • SL/TP   │      │ • CRUD    │      │   60 seg    │              │   │
│  │  │ • Update  │      │ • History │      │ • HOLD      │              │   │
│  │  │ • Cancel  │      │ • Stats   │      │ • TIGHTEN_SL│              │   │
│  │  └─────┬─────┘      └─────┬─────┘      │ • EXTEND_TP │              │   │
│  │        │                  │            └──────┬──────┘              │   │
│  │        ▼                  ▼                   │                     │   │
│  │  ┌───────────┐      ┌───────────┐            │                     │   │
│  │  │ EXCHANGE  │      │positions.db│◄───────────┘                     │   │
│  │  │(Binance)  │      │           │                                   │   │
│  │  └───────────┘      └───────────┘                                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                 │                                           │
│  ┌──────────────────────────────▼────────────────────────────────────────┐  │
│  │                    NOTIFICATION MANAGER                                │  │
│  │   • Trade ejecutado  • SL/TP triggered  • Trailing update             │  │
│  │   • Ajuste IA        • Kill switch      • Daily summary               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                 │                                           │
│                                 ▼                                           │
│                           ┌──────────┐                                      │
│                           │ TELEGRAM │                                      │
│                           └──────────┘                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Flujo de Operación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUJO DE UNA OPERACIÓN                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. ANÁLISIS
   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
   │  Market  │────►│Technical │────►│    AI    │────►│   Risk   │
   │  Engine  │     │ Analyzer │     │  Engine  │     │ Manager  │
   │  (OHLCV) │     │  (RSI,   │     │ (Agentes)│     │ (Kelly)  │
   │          │     │   MACD)  │     │          │     │          │
   └──────────┘     └──────────┘     └──────────┘     └────┬─────┘
                                                           │
                                    ┌──────────────────────┘
                                    │
                                    ▼ SI: Señal válida + Risk OK
2. EJECUCIÓN
   ┌──────────────────────────────────────────────────────────────┐
   │                     MARKET ENGINE                             │
   │                                                               │
   │    ┌─────────────┐         ┌─────────────┐                   │
   │    │ Verificar   │────────►│  Ejecutar   │                   │
   │    │ precio      │         │  orden      │                   │
   │    │ (anti-slip) │         │  (limit)    │                   │
   │    └─────────────┘         └──────┬──────┘                   │
   │                                   │                          │
   └───────────────────────────────────┼──────────────────────────┘
                                       │
                                       ▼ Orden ejecutada
3. PROTECCIÓN
   ┌──────────────────────────────────────────────────────────────┐
   │                   POSITION ENGINE                             │
   │                                                               │
   │    ┌─────────────┐         ┌─────────────┐                   │
   │    │   Crear     │────────►│  Colocar    │                   │
   │    │  posición   │         │   OCO       │                   │
   │    │  (SQLite)   │         │ (SL + TP)   │                   │
   │    └─────────────┘         └──────┬──────┘                   │
   │                                   │                          │
   └───────────────────────────────────┼──────────────────────────┘
                                       │
                                       ▼ OCO activo en exchange
4. MONITOREO (Loop en background)
   ┌──────────────────────────────────────────────────────────────┐
   │                   MONITORING LOOP                             │
   │                                                               │
   │    Cada 500ms:                                                │
   │    ┌─────────────┐                                           │
   │    │ Verificar   │──► ¿TP filled? ──► Cerrar posición        │
   │    │ estado OCO  │                                           │
   │    │             │──► ¿SL filled? ──► Cerrar posición        │
   │    └─────────────┘                                           │
   │                                                               │
   │    ┌─────────────┐                                           │
   │    │ Trailing    │──► ¿Profit > 1.5%? ──► Mover SL           │
   │    │ Stop check  │                                           │
   │    └─────────────┘                                           │
   │                                                               │
   │    Cada 60s (IA Supervisor):                                  │
   │    ┌─────────────┐                                           │
   │    │ Supervisor  │──► HOLD / TIGHTEN_SL / EXTEND_TP          │
   │    │    IA       │                                           │
   │    └─────────────┘                                           │
   │                                                               │
   └──────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ SL o TP ejecutado
5. CIERRE
   ┌──────────────────────────────────────────────────────────────┐
   │    ┌─────────────┐         ┌─────────────┐                   │
   │    │  Registrar  │────────►│  Notificar  │                   │
   │    │  resultado  │         │  Telegram   │                   │
   │    │  (SQLite)   │         │             │                   │
   │    └─────────────┘         └─────────────┘                   │
   │                                                               │
   │    trade_history: {pnl, pnl_percent, exit_reason, hold_time} │
   └──────────────────────────────────────────────────────────────┘
```

## Requisitos Previos

- Python 3.9 o superior
- Docker y Docker Compose (recomendado para producción)
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

### 4. Configurar variables de entorno

```bash
cp .env.example .env
nano .env  # o usa tu editor favorito
```

Rellena tus credenciales en `.env`:

```env
# IA
DEEPSEEK_API_KEY=sk-tu-clave-aqui

# Exchange (Binance)
BINANCE_API_KEY=tu-api-key
BINANCE_API_SECRET=tu-secret

# Notificaciones (opcional)
TELEGRAM_BOT_TOKEN=tu-token
TELEGRAM_CHAT_ID=tu-chat-id
```

### 5. Configurar el bot

Edita `config/config_live.yaml` según tus preferencias. Ver sección de configuración abajo.

## Uso

### Modo Local

```bash
source venv/bin/activate
python main.py
```

### Modo Docker (Recomendado para producción)

```bash
docker compose up -d --build
docker logs -f sath_bot
```

## Configuración de Gestión de Posiciones

```yaml
# config/config_live.yaml

position_management:
  enabled: true

  # Método de protección SL/TP
  # "oco" = Exchange maneja automáticamente (recomendado)
  # "local" = Bot monitorea y ejecuta
  protection_mode: "oco"

  # Configuración de órdenes OCO
  oco_settings:
    enabled: true
    sl_limit_buffer_percent: 0.2  # Buffer entre stop trigger y limit price

  # Monitoreo local (fallback si OCO no disponible)
  local_monitoring:
    enabled: true
    check_interval_ms: 500  # Verificar cada 500ms

  # Trailing Stop inteligente
  trailing_stop:
    enabled: true
    activation_profit_percent: 1.5  # Activar después de 1.5% profit
    trail_distance_percent: 2.0     # Mantener 2% detrás del precio

  # Supervisión IA de posiciones
  supervision:
    enabled: true
    check_interval_seconds: 60  # Cada minuto
    actions_allowed:
      - "HOLD"        # Mantener sin cambios
      - "TIGHTEN_SL"  # Acercar SL para asegurar ganancias
      - "EXTEND_TP"   # Extender TP si momentum fuerte
    # NO incluye PARTIAL_CLOSE ni FULL_CLOSE (modo conservador)

  # Límites del portfolio
  portfolio:
    max_concurrent_positions: 3    # Máximo 3 posiciones abiertas
    max_exposure_percent: 50       # Máximo 50% del capital desplegado
    max_per_symbol_percent: 25     # Máximo 25% en un solo símbolo

  # Persistencia (SQLite)
  database:
    path: "data/positions.db"
```

## Estructura del Proyecto

```
bot/
├── config/
│   ├── config.yaml              # Configuración para paper trading
│   └── config_live.yaml         # Configuración para trading real
├── src/
│   ├── engines/
│   │   ├── ai_engine.py         # Motor de IA con agentes especializados
│   │   ├── market_engine.py     # Conexión con exchanges + órdenes OCO
│   │   ├── position_engine.py   # Motor de gestión de posiciones (v1.5)
│   │   └── websocket_engine.py  # Motor de datos en tiempo real
│   ├── modules/
│   │   ├── technical_analysis.py   # Indicadores técnicos
│   │   ├── risk_manager.py         # Gestión de riesgo + Kelly
│   │   ├── order_manager.py        # Órdenes OCO/SL/TP (v1.5)
│   │   ├── position_store.py       # Persistencia SQLite (v1.5)
│   │   ├── position_supervisor.py  # Agente IA supervisor (v1.5)
│   │   ├── data_logger.py          # Logging InfluxDB
│   │   └── notifications.py        # Alertas Telegram
│   └── schemas/
│       ├── ai_responses.py         # Schemas de respuestas IA
│       └── position_schemas.py     # Modelos de posiciones (v1.5)
├── data/
│   └── positions.db             # Base de datos SQLite de posiciones
├── logs/
│   └── trading_bot.log          # Logs del sistema
├── main.py                      # Orquestador principal
├── requirements.txt             # Dependencias Python
├── docker-compose.yml           # Orquestación Docker
├── Dockerfile                   # Imagen Docker del bot
├── .env                         # Credenciales (NO subir a git)
├── README.md                    # Esta documentación
├── CHANGELOG.md                 # Historial de cambios
└── HYBRID_ARCHITECTURE.md       # Arquitectura IA híbrida
```

## Gestión de Riesgo

### Kill Switch
Si el bot pierde más del 5% del capital total, se apaga automáticamente por 24 horas.

### Kelly Criterion
Ajusta dinámicamente el tamaño de posición basado en la confianza de la señal de IA.

### Trailing Stop
El stop loss sube automáticamente con el precio para asegurar ganancias.

### Portfolio Limits
- Máximo 3 posiciones concurrentes
- Máximo 50% del capital desplegado
- Máximo 25% en un solo símbolo

## Notificaciones Telegram

El bot envía alertas para:
- Operaciones ejecutadas
- Stop Loss triggered
- Take Profit alcanzado
- Trailing stop actualizado
- Ajustes IA de posiciones
- Kill switch activado

## Solución de Problemas

### El bot no crea posiciones protegidas
1. Verifica que `position_management.enabled: true` en config
2. Revisa los logs para errores de inicialización
3. Verifica que el exchange soporta órdenes OCO

### Las órdenes OCO no se colocan
1. Verifica permisos de API en el exchange
2. Revisa que el símbolo soporte OCO
3. El bot usará órdenes separadas como fallback

### Posiciones no se recuperan al reiniciar
1. Verifica que existe `data/positions.db`
2. Revisa permisos de escritura en el directorio `data/`

## Changelog

Ver [CHANGELOG.md](CHANGELOG.md) para historial completo de cambios.

### v1.5 (Diciembre 2024)
- Sistema completo de gestión de posiciones
- Órdenes OCO reales (Stop Loss + Take Profit)
- Supervisión IA de posiciones (HOLD, TIGHTEN_SL, EXTEND_TP)
- Trailing Stop inteligente con activación configurable
- Persistencia SQLite (sobrevive reinicios)
- Portfolio limits (max posiciones, max exposición)
- Notificaciones de eventos de posición

---

**Desarrollado con ❤️ para traders algorítmicos**

Versión 1.5 - Diciembre 2024
