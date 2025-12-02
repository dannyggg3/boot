# Arquitectura del Sistema SATH v1.5

Este documento describe la arquitectura completa del Sistema Autónomo de Trading Híbrido.

## Árbol de Archivos

```
bot/
│
├── main.py                           # Orquestador principal del sistema
│   ├── TradingBot                    # Clase principal
│   │   ├── __init__()                # Inicializa todos los componentes
│   │   ├── run()                     # Loop principal de trading
│   │   ├── _analyze_symbol()         # Análisis por símbolo
│   │   ├── _execute_trade()          # Ejecuta operaciones
│   │   └── _shutdown()               # Apagado limpio
│   └── main()                        # Punto de entrada
│
├── config/
│   ├── config.yaml                   # Configuración paper trading
│   └── config_live.yaml              # Configuración trading real
│       ├── trading                   # Símbolos, modo, intervalos
│       ├── risk_management           # Kill switch, Kelly, sizing
│       ├── position_management       # OCO, trailing, supervisión
│       ├── technical_analysis        # Indicadores
│       └── notifications             # Telegram
│
├── src/
│   │
│   ├── engines/                      # Motores principales
│   │   │
│   │   ├── ai_engine.py              # Motor de IA
│   │   │   ├── AIEngine
│   │   │   │   ├── analyze_market_hybrid()   # Análisis híbrido 4 niveles
│   │   │   │   ├── _local_pre_filter()       # Nivel 0: Filtro local
│   │   │   │   ├── _check_cache()            # Nivel 0.5: Cache
│   │   │   │   ├── _fast_filter()            # Nivel 1: Filtro rápido
│   │   │   │   └── _deep_analysis()          # Nivel 2: Análisis profundo
│   │   │   └── Agentes Especializados
│   │   │       ├── Agente Tendencia          # RSI 30-70
│   │   │       └── Agente Reversión          # RSI extremos
│   │   │
│   │   ├── market_engine.py          # Motor de mercado
│   │   │   ├── MarketEngine
│   │   │   │   ├── get_ohlcv()               # Datos OHLCV
│   │   │   │   ├── get_current_price()       # Precio actual
│   │   │   │   ├── get_order_book()          # Order book
│   │   │   │   ├── execute_order()           # Ejecutar orden
│   │   │   │   ├── create_oco_order()        # [v1.5] Crear OCO
│   │   │   │   ├── cancel_oco_order()        # [v1.5] Cancelar OCO
│   │   │   │   ├── check_oco_status()        # [v1.5] Estado OCO
│   │   │   │   └── update_stop_loss_order()  # [v1.5] Actualizar SL
│   │   │   └── Conexiones
│   │   │       ├── Binance (CCXT)
│   │   │       ├── Bybit (CCXT)
│   │   │       └── Interactive Brokers (IB)
│   │   │
│   │   ├── position_engine.py        # [v1.5] Motor de posiciones
│   │   │   └── PositionEngine
│   │   │       ├── create_position()         # Crear posición
│   │   │       ├── close_position()          # Cerrar posición
│   │   │       ├── start_monitoring()        # Iniciar monitoreo
│   │   │       ├── _monitoring_loop()        # Loop de monitoreo
│   │   │       ├── _check_sl_tp_triggers()   # Verificar SL/TP
│   │   │       ├── _check_trailing_stop()    # Trailing stop
│   │   │       ├── recover_positions_on_startup()  # Recuperar
│   │   │       └── get_portfolio_status()    # Estado portfolio
│   │   │
│   │   └── websocket_engine.py       # Motor WebSocket (opcional)
│   │       └── WebSocketEngine
│   │           ├── connect()
│   │           ├── subscribe_ticker()
│   │           └── get_latest_price()
│   │
│   ├── modules/                      # Módulos auxiliares
│   │   │
│   │   ├── technical_analysis.py     # Análisis técnico
│   │   │   └── TechnicalAnalyzer
│   │   │       ├── calculate_rsi()
│   │   │       ├── calculate_macd()
│   │   │       ├── calculate_ema()
│   │   │       ├── calculate_bollinger()
│   │   │       └── calculate_atr()
│   │   │
│   │   ├── risk_manager.py           # Gestión de riesgo
│   │   │   └── RiskManager
│   │   │       ├── validate_trade()
│   │   │       ├── calculate_kelly_position_size()
│   │   │       ├── check_kill_switch()
│   │   │       ├── calculate_stop_loss()
│   │   │       └── calculate_take_profit()
│   │   │
│   │   ├── order_manager.py          # [v1.5] Gestión de órdenes
│   │   │   └── OrderManager
│   │   │       ├── place_oco_order()
│   │   │       ├── cancel_oco_order()
│   │   │       ├── update_stop_loss()
│   │   │       ├── check_oco_status()
│   │   │       └── place_market_close()
│   │   │
│   │   ├── position_store.py         # [v1.5] Persistencia SQLite
│   │   │   └── PositionStore
│   │   │       ├── save_position()
│   │   │       ├── get_position()
│   │   │       ├── get_open_positions()
│   │   │       ├── close_position()
│   │   │       ├── update_stop_loss()
│   │   │       ├── record_trade()
│   │   │       └── get_trade_stats()
│   │   │
│   │   ├── position_supervisor.py    # [v1.5] Supervisión IA
│   │   │   └── PositionSupervisor
│   │   │       ├── supervise_position()
│   │   │       ├── _build_supervision_prompt()
│   │   │       ├── _local_supervision()
│   │   │       ├── _validate_new_stop_loss()
│   │   │       └── supervise_all_positions()
│   │   │
│   │   ├── data_logger.py            # Logging InfluxDB
│   │   │   └── DataLogger
│   │   │       ├── log_decision()
│   │   │       ├── log_trade()
│   │   │       └── log_result()
│   │   │
│   │   └── notifications.py          # Notificaciones Telegram
│   │       └── NotificationManager
│   │           ├── notify_startup()
│   │           ├── notify_trade_executed()
│   │           ├── notify_sl_hit()           # [v1.5]
│   │           ├── notify_tp_hit()           # [v1.5]
│   │           ├── notify_trailing_update()  # [v1.5]
│   │           ├── notify_ai_adjustment()    # [v1.5]
│   │           └── notify_position_closed()  # [v1.5]
│   │
│   └── schemas/                      # Modelos de datos
│       │
│       ├── ai_responses.py           # Respuestas de IA
│       │   ├── AIDecision
│       │   ├── MarketAnalysis
│       │   └── TradeSignal
│       │
│       └── position_schemas.py       # [v1.5] Schemas de posiciones
│           ├── Enums
│           │   ├── PositionStatus    # pending, open, closing, closed
│           │   ├── PositionSide      # long, short
│           │   ├── ExitReason        # stop_loss, take_profit, etc
│           │   ├── OrderType         # market, limit, oco
│           │   └── SupervisorAction  # HOLD, TIGHTEN_SL, EXTEND_TP
│           ├── Position              # Modelo de posición
│           ├── Order                 # Modelo de orden
│           ├── TradeResult           # Resultado de trade
│           ├── SupervisorDecision    # Decisión del supervisor
│           └── PortfolioExposure     # Exposición del portfolio
│
├── data/
│   └── positions.db                  # [v1.5] Base de datos SQLite
│       ├── positions                 # Tabla de posiciones
│       ├── orders                    # Tabla de órdenes
│       └── trade_history             # Historial de trades
│
├── logs/
│   └── trading_bot.log               # Logs del sistema
│
└── docs/
    └── ARCHITECTURE.md               # Este archivo
```

## Flujo de Datos Principal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CICLO DE TRADING                                │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   main.py run() │
                              │   Loop cada 60s │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
            ┌───────────┐      ┌───────────┐      ┌───────────┐
            │ BTC/USDT  │      │ ETH/USDT  │      │ SOL/USDT  │
            └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
                  │                  │                  │
                  └──────────────────┼──────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            _analyze_symbol()                                 │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │  Market Engine  │───►│   Technical     │───►│   AI Engine     │          │
│  │  get_ohlcv()    │    │   Analyzer      │    │                 │          │
│  │  get_order_book │    │  RSI,MACD,EMA   │    │ Nivel 0: Local  │          │
│  └─────────────────┘    └─────────────────┘    │ Nivel 1: Fast   │          │
│                                                │ Nivel 2: Deep   │          │
│                                                └────────┬────────┘          │
│                                                         │                   │
│                                              COMPRA / VENTA / ESPERA        │
└─────────────────────────────────────────────────────────┼───────────────────┘
                                                          │
                               ┌──────────────────────────┘
                               │ SI: COMPRA o VENTA
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Risk Manager                                    │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ validate_trade  │───►│ Kelly Criterion │───►│ Position Size   │          │
│  │ check_kill_sw.  │    │ (confianza IA)  │    │ SL, TP calc     │          │
│  └─────────────────┘    └─────────────────┘    └────────┬────────┘          │
│                                                         │                   │
│                                                   risk_params               │
└─────────────────────────────────────────────────────────┼───────────────────┘
                                                          │
                               ┌──────────────────────────┘
                               │ SI: Risk OK
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            _execute_trade()                                  │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ Market Engine   │───►│ execute_order() │───►│ Telegram notify │          │
│  │ verify price    │    │ (limit/market)  │    │ trade_executed  │          │
│  └─────────────────┘    └─────────────────┘    └────────┬────────┘          │
│                                                         │                   │
│                                                   order_result              │
└─────────────────────────────────────────────────────────┼───────────────────┘
                                                          │
                               ┌──────────────────────────┘
                               │ SI: Orden ejecutada
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     POSITION MANAGEMENT SYSTEM v1.5                          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Position Engine                               │    │
│  │                                                                      │    │
│  │  ┌─────────────────┐                                                │    │
│  │  │ create_position │                                                │    │
│  │  │  • Crear ID     │                                                │    │
│  │  │  • Calcular P&L │                                                │    │
│  │  │  • Guardar      │                                                │    │
│  │  └────────┬────────┘                                                │    │
│  │           │                                                         │    │
│  │           ├────────────────────┬────────────────────┐              │    │
│  │           │                    │                    │              │    │
│  │           ▼                    ▼                    ▼              │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │    │
│  │  │ Position Store  │  │ Order Manager   │  │ Notifications   │    │    │
│  │  │ save_position() │  │ place_oco_order │  │ position_created│    │    │
│  │  │                 │  │ (SL + TP)       │  │                 │    │    │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────────┘    │    │
│  │           │                    │                                   │    │
│  │           ▼                    ▼                                   │    │
│  │  ┌─────────────────┐  ┌─────────────────┐                         │    │
│  │  │ positions.db    │  │    Exchange     │                         │    │
│  │  │ (SQLite)        │  │   (Binance)     │                         │    │
│  │  └─────────────────┘  └─────────────────┘                         │    │
│  │                                                                    │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Flujo de Monitoreo de Posiciones

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MONITORING LOOP (Background Thread)                     │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │ start_monitoring│
                              │ Thread daemon   │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │_monitoring_loop │◄──────────────────┐
                              │  (while active) │                   │
                              └────────┬────────┘                   │
                                       │                            │
                                       ▼                            │
                    ┌──────────────────────────────────┐            │
                    │     Para cada posición abierta    │            │
                    └────────────────┬─────────────────┘            │
                                     │                              │
                    ┌────────────────┼────────────────┐             │
                    │                │                │             │
                    ▼                ▼                ▼             │
           ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
           │ Check OCO   │  │  Trailing   │  │ Supervisor  │       │
           │   Status    │  │   Stop      │  │    IA       │       │
           │ (cada 500ms)│  │ (cada 500ms)│  │ (cada 60s)  │       │
           └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
                  │                │                │               │
                  │                │                │               │
      ┌───────────┼────────┐       │       ┌───────┼───────┐       │
      │           │        │       │       │       │       │       │
      ▼           ▼        ▼       ▼       ▼       ▼       ▼       │
 ┌────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐ │
 │TP Hit  │ │SL Hit  │ │Active│ │Update│ │NoUpd │ │TIGHT │ │HOLD │ │
 └───┬────┘ └───┬────┘ └──────┘ │  SL  │ └──────┘ │  SL  │ └──┬──┘ │
     │          │               └──┬───┘          └──┬───┘    │    │
     │          │                  │                 │        │    │
     │          │                  │                 │        │    │
     ▼          ▼                  ▼                 ▼        │    │
┌──────────────────────────────────────────────────────────┐  │    │
│                    close_position()                       │  │    │
│                                                          │  │    │
│  ┌─────────────────┐   ┌─────────────────┐              │  │    │
│  │ Order Manager   │   │ Position Store  │              │  │    │
│  │ cancel_oco()    │   │ close_position()│              │  │    │
│  └─────────────────┘   │ record_trade()  │              │  │    │
│                        └─────────────────┘              │  │    │
│                                                          │  │    │
│  ┌─────────────────┐                                    │  │    │
│  │  Notifications  │                                    │  │    │
│  │  • sl_hit       │                                    │  │    │
│  │  • tp_hit       │                                    │  │    │
│  │  • pos_closed   │                                    │  │    │
│  └─────────────────┘                                    │  │    │
└──────────────────────────────────────────────────────────┘  │    │
                                                              │    │
                               ┌───────────────────────────────┘    │
                               │                                    │
                               ▼                                    │
                      ┌─────────────────┐                           │
                      │  update_sl()    │                           │
                      │  Order Manager  │                           │
                      │  Position Store │                           │
                      │  Notifications  │                           │
                      └─────────────────┘                           │
                                                                    │
                               ┌─────────────────────────────────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │  sleep(500ms)   │
                      └────────┬────────┘
                               │
                               └──────────────► (loop)
```

## Estados de una Posición

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CICLO DE VIDA DE POSICIÓN                          │
└──────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                                      │
    │  PENDING                    OPEN                      CLOSED        │
    │  ────────                   ────                      ──────        │
    │                                                                      │
    │  ┌──────────┐          ┌──────────────┐          ┌──────────────┐  │
    │  │          │  orden   │              │  SL/TP   │              │  │
    │  │ PENDING  │─────────►│     OPEN     │─────────►│    CLOSED    │  │
    │  │          │  filled  │              │  hit     │              │  │
    │  └──────────┘          └───────┬──────┘          └──────────────┘  │
    │                                │                                    │
    │                                │ Mientras OPEN:                     │
    │                                │                                    │
    │                        ┌───────┴───────┐                           │
    │                        │               │                           │
    │                        ▼               ▼                           │
    │              ┌──────────────┐  ┌──────────────┐                    │
    │              │   Trailing   │  │  Supervisor  │                    │
    │              │    Stop      │  │     IA       │                    │
    │              │   activo     │  │    ajusta    │                    │
    │              └──────────────┘  └──────────────┘                    │
    │                                                                      │
    └─────────────────────────────────────────────────────────────────────┘

    Exit Reasons:
    ├── stop_loss       → SL trigger ejecutado
    ├── take_profit     → TP alcanzado
    ├── trailing_stop   → Trailing SL ejecutado
    ├── ai_decision     → IA decidió cerrar
    ├── manual          → Usuario cerró manualmente
    ├── kill_switch     → Kill switch activado
    └── error           → Error en el sistema
```

## Base de Datos SQLite

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            positions.db                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TABLA: positions                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ id                TEXT PRIMARY KEY     # UUID corto (8 chars)               │
│ symbol            TEXT NOT NULL        # "BTC/USDT"                         │
│ side              TEXT NOT NULL        # "long" | "short"                   │
│ status            TEXT NOT NULL        # "open" | "closed"                  │
│ entry_price       REAL                 # Precio de entrada                  │
│ quantity          REAL                 # Cantidad                           │
│ entry_time        TEXT                 # ISO timestamp                      │
│ entry_order_id    TEXT                 # ID orden de entrada                │
│ confidence        REAL                 # Confianza IA (0-1)                 │
│ agent_type        TEXT                 # "tendencia" | "reversion"          │
│ stop_loss         REAL                 # SL actual                          │
│ take_profit       REAL                 # TP actual                          │
│ initial_stop_loss REAL                 # SL original                        │
│ trailing_active   INTEGER              # 0 | 1                              │
│ oco_order_id      TEXT                 # ID orden OCO                       │
│ sl_order_id       TEXT                 # ID orden SL                        │
│ tp_order_id       TEXT                 # ID orden TP                        │
│ exit_price        REAL                 # Precio de salida                   │
│ exit_time         TEXT                 # ISO timestamp                      │
│ exit_reason       TEXT                 # stop_loss, take_profit, etc        │
│ realized_pnl      REAL                 # P&L realizado                      │
│ realized_pnl_pct  REAL                 # P&L %                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TABLA: orders                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ id                TEXT PRIMARY KEY     # ID de la orden                     │
│ position_id       TEXT                 # FK a positions                     │
│ symbol            TEXT NOT NULL        # "BTC/USDT"                         │
│ type              TEXT NOT NULL        # "limit", "oco", "stop_loss"        │
│ side              TEXT NOT NULL        # "buy" | "sell"                     │
│ status            TEXT NOT NULL        # "open", "filled", "cancelled"      │
│ quantity          REAL                 # Cantidad                           │
│ price             REAL                 # Precio (para limit)                │
│ stop_price        REAL                 # Precio stop (para SL)              │
│ filled_quantity   REAL                 # Cantidad ejecutada                 │
│ average_fill      REAL                 # Precio promedio de fill            │
│ created_at        TEXT                 # ISO timestamp                      │
│ filled_at         TEXT                 # ISO timestamp                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TABLA: trade_history                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ id                TEXT PRIMARY KEY     # UUID                               │
│ position_id       TEXT NOT NULL        # FK a positions                     │
│ symbol            TEXT NOT NULL        # "BTC/USDT"                         │
│ side              TEXT NOT NULL        # "long" | "short"                   │
│ entry_price       REAL                 # Precio entrada                     │
│ exit_price        REAL                 # Precio salida                      │
│ quantity          REAL                 # Cantidad                           │
│ pnl               REAL                 # P&L en USD                         │
│ pnl_percent       REAL                 # P&L %                              │
│ result            TEXT                 # "win" | "loss" | "breakeven"       │
│ entry_time        TEXT                 # ISO timestamp                      │
│ exit_time         TEXT                 # ISO timestamp                      │
│ hold_time_min     INTEGER              # Minutos en posición                │
│ exit_reason       TEXT                 # stop_loss, take_profit, etc        │
│ agent_type        TEXT                 # Agente que generó señal            │
│ confidence        REAL                 # Confianza IA                       │
│ created_at        TEXT                 # ISO timestamp                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Dependencias entre Módulos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GRAFO DE DEPENDENCIAS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                              main.py
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
    ┌───────────┐         ┌───────────┐         ┌───────────┐
    │ AIEngine  │         │ Market    │         │ Risk      │
    │           │         │ Engine    │         │ Manager   │
    └─────┬─────┘         └─────┬─────┘         └───────────┘
          │                     │
          │                     │
          ▼                     ▼
    ┌───────────┐         ┌───────────┐
    │ Technical │         │ Position  │◄─────┐
    │ Analyzer  │         │ Engine    │      │
    └───────────┘         └─────┬─────┘      │
                                │            │
              ┌─────────────────┼────────────┤
              │                 │            │
              ▼                 ▼            ▼
        ┌───────────┐    ┌───────────┐ ┌───────────┐
        │ Order     │    │ Position  │ │ Position  │
        │ Manager   │    │ Store     │ │ Supervisor│
        └─────┬─────┘    └───────────┘ └───────────┘
              │
              ▼
        ┌───────────┐
        │ Exchange  │
        │ (CCXT)    │
        └───────────┘

        ─────────────────────────────────────────────────

                      Notifications
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │   main    │   │ Position  │   │ Risk      │
    │           │   │ Engine    │   │ Manager   │
    └───────────┘   └───────────┘   └───────────┘
```

---

**Última actualización**: Diciembre 2024 - v1.5.1
