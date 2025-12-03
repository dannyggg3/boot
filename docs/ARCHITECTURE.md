# Arquitectura del Sistema SATH v1.9.0 INSTITUCIONAL PRO MAX ★★★★★

Este documento describe la arquitectura completa del Sistema Autónomo de Trading Híbrido - Nivel Institucional Máximo.

## Cambios v1.9.0 (INSTITUCIONAL PRO MAX)

### Mejoras Críticas v1.9.0

| Mejora | Descripción | Impacto |
|--------|-------------|---------|
| **Validación Post-IA** | Re-verifica precio antes de ejecutar | Elimina trades con R/R inválido |
| **Filtro ADX** | Bloquea mercados laterales (ADX < 20) | -40% costos API, mejores trades |
| **Backtester** | Motor de validación de estrategias | Testing antes de live |
| **CI/CD Pipeline** | GitHub Actions completo | Calidad garantizada |
| **Métricas Abortados** | Tracking de trades cancelados | Visibilidad total |

### Archivos Nuevos v1.9.0

| Archivo | Descripción |
|---------|-------------|
| `src/modules/backtester.py` | Motor de backtesting con 5 estrategias |
| `.github/workflows/ci.yml` | Pipeline CI/CD completo |
| `CHANGELOG.md` | Historial de cambios |

### Validación Precio Post-IA (main.py:1085-1156)

```
┌─────────────────────────────────────────────────────────────┐
│                 FLUJO VALIDACIÓN POST-IA v1.9               │
└─────────────────────────────────────────────────────────────┘

         IA Analiza                    Antes de Ejecutar
         (Precio X)                    (Re-consulta Precio)
              │                              │
              ▼                              ▼
     ┌────────────────┐            ┌────────────────┐
     │ analysis_price │            │ current_price  │
     │   $100,000     │            │   $100,250     │
     └────────────────┘            └────────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │ Desviación  │
                                   │   0.25%     │
                                   └──────┬──────┘
                                          │
                              ┌───────────┴───────────┐
                              │                       │
                              ▼                       ▼
                    ┌─────────────────┐     ┌─────────────────┐
                    │  > 0.2% umbral  │     │  ≤ 0.2% umbral  │
                    │   ❌ ABORTAR    │     │   ✅ EJECUTAR   │
                    └─────────────────┘     └─────────────────┘
```

### Filtro ADX Pre-IA (ai_engine.py:159-176)

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO FILTRO ADX v1.9                    │
└─────────────────────────────────────────────────────────────┘

                    Datos Técnicos
                          │
                          ▼
               ┌────────────────────┐
               │    Calcular ADX    │
               │ (technical_analysis)│
               └──────────┬─────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
     ┌────────────────┐      ┌────────────────┐
     │   ADX < 20     │      │   ADX >= 20    │
     │  Sin Tendencia │      │   Tendencia    │
     └───────┬────────┘      └───────┬────────┘
             │                       │
             ▼                       ▼
     ┌────────────────┐      ┌────────────────┐
     │  🚫 BLOQUEAR   │      │  ✅ Continuar  │
     │  No llamar IA  │      │  a análisis IA │
     │  $0 gastado    │      └────────────────┘
     └────────────────┘
```

---

## Cambios v1.8.1 (INSTITUCIONAL PRO ★★★★★)

### Optimizaciones v1.8.1

| Componente | v1.7+ | v1.8.1 | Impacto |
|------------|-------|--------|---------|
| **Confianza mínima** | 60% | 70-75% | Menos trades, mayor calidad |
| **R/R mínimo** | 1.5 | 2.0 | Mejor expectativa matemática |
| **MTF Alignment** | 70% | 75-80% | Menos señales falsas |
| **Profit/Fees ratio** | 5x | 8-10x | Solo trades rentables |
| **Kelly fraction** | 1/5 | 1/4-1/5 | Mejor aprovechamiento |
| **ATR Stops** | Básico | Avanzado | R/R dinámico garantizado |

### Nuevas Características v1.8.1

- **ATR-Based Stop Loss**: SL dinámico basado en volatilidad real (2x ATR)
- **ATR-Based Take Profit**: TP automático garantizando R/R 2:1 (4x ATR)
- **Session Filter**: Solo opera en horarios de máxima liquidez
- **API Retries**: Reintentos configurables para errores de conexión
- **Trailing Stop Mejorado**: Cooldown + safety margin configurables

---

## Cambios v1.7+ (Nivel Institucional Superior)

### Nuevos Módulos v1.7+

| Módulo | Descripción | Archivo |
|--------|-------------|---------|
| **Multi-Timeframe** | Solo opera cuando 4H→1H→15m están alineados | `multi_timeframe.py` |
| **Correlation Filter** | Bloquea trades si correlación >70% con posición existente | `correlation_filter.py` |
| **Adaptive Parameters** | Auto-ajusta confianza/riesgo según rendimiento | `adaptive_parameters.py` |
| **Performance Attribution** | Análisis de alpha por agente/régimen/hora | `performance_attribution.py` |

### Hotfix v1.7.1 - Compatibilidad Testnet/Paper

| Componente | Cambio | Archivo |
|------------|--------|---------|
| Technical Analysis | Mínimo velas adaptativo (50 paper, 200 live) | `technical_analysis.py` |
| Technical Analysis | EMAs adaptativas según datos disponibles | `technical_analysis.py` |
| Adaptive Parameters | Hysteresis 5 min en cambios de volatilidad | `adaptive_parameters.py` |
| Main | Logging mejorado de velas recibidas | `main.py` |

**Comportamiento por Modo:**
```
Paper/Testnet:
  - Mínimo: 50 velas
  - EMAs: 12/26 (si <100 velas) o 20/100 (si <200 velas)

Live:
  - Mínimo: 200 velas
  - EMAs: 50/200 (estándar institucional)
```

### Mejoras Anteriores v1.7

| Componente | Cambio | Archivo |
|------------|--------|---------|
| Trailing Stop | Fix race condition + cooldown 3s | `position_engine.py` |
| Paper Mode | Simulador latencia/slippage | `order_manager.py` |
| Kelly Criterion | Auto-update en cierre + conservador | `risk_manager.py` |
| Métricas | Sharpe, Sortino, Calmar, Fill Rate | `institutional_metrics.py` |
| Liquidez | Validación pre-ejecución | `market_engine.py` |
| Singletons | Thread-safe | `position_store.py` |
| R/R Validation | RECHAZA trades con R/R < 1.5 | `risk_manager.py` |

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
│   │   ├── technical_analysis.py     # Análisis técnico [v1.7.1]
│   │   │   └── TechnicalAnalyzer
│   │   │       ├── analyze()                 # Análisis completo
│   │   │       ├── _adjust_ema_periods()     # [v1.7.1] EMAs adaptativas
│   │   │       ├── _calculate_rsi()
│   │   │       ├── _calculate_macd()
│   │   │       ├── _calculate_ema()          # Usa períodos adaptativos
│   │   │       ├── _calculate_bollinger()
│   │   │       └── _calculate_atr()
│   │   │
│   │   ├── risk_manager.py           # Gestión de riesgo
│   │   │   └── RiskManager
│   │   │       ├── validate_trade()
│   │   │       ├── calculate_kelly_position_size()
│   │   │       ├── check_kill_switch()
│   │   │       ├── calculate_stop_loss()
│   │   │       └── calculate_take_profit()
│   │   │
│   │   ├── order_manager.py          # [v1.5+v1.7] Gestión de órdenes
│   │   │   ├── OrderManager
│   │   │   │   ├── place_oco_order()
│   │   │   │   ├── cancel_oco_order()
│   │   │   │   ├── update_stop_loss()
│   │   │   │   ├── check_oco_status()
│   │   │   │   └── place_market_close()
│   │   │   └── PaperModeSimulator        # [v1.7] Simulación realista
│   │   │       ├── simulate_latency()
│   │   │       ├── calculate_slippage()
│   │   │       ├── process_order()
│   │   │       └── get_stats()
│   │   │
│   │   ├── institutional_metrics.py  # [v1.7] Métricas institucionales
│   │   │   └── InstitutionalMetrics
│   │   │       ├── record_trade()
│   │   │       ├── record_daily_return()
│   │   │       ├── calculate_sharpe_ratio()
│   │   │       ├── calculate_sortino_ratio()
│   │   │       ├── calculate_calmar_ratio()
│   │   │       ├── get_regime_stats()
│   │   │       ├── get_latency_stats()
│   │   │       └── get_comprehensive_report()
│   │   │
│   │   ├── multi_timeframe.py        # [v1.7+] Análisis Multi-Timeframe
│   │   │   └── MultiTimeframeAnalyzer
│   │   │       ├── analyze_timeframe()           # Analiza un TF individual
│   │   │       ├── get_mtf_filter_result()       # Resultado filtro MTF
│   │   │       ├── _calculate_alignment_score()  # Calcula alineación
│   │   │       └── _calculate_confidence_boost() # Boost de confianza
│   │   │
│   │   ├── correlation_filter.py     # [v1.7+] Filtro de Correlación
│   │   │   └── CorrelationFilter
│   │   │       ├── can_open_position()          # Verifica si puede abrir
│   │   │       ├── get_diversification_score()  # Score diversificación
│   │   │       ├── update_correlation()         # Actualiza correlación
│   │   │       └── _get_correlation()           # Obtiene correlación par
│   │   │
│   │   ├── adaptive_parameters.py    # [v1.7+] Parámetros Adaptativos
│   │   │   └── AdaptiveParameterManager
│   │   │       ├── update_from_trade()          # Actualiza con trade
│   │   │       ├── update_volatility()          # Actualiza volatilidad
│   │   │       ├── get_adjusted_confidence()    # Confianza ajustada
│   │   │       ├── get_adjusted_risk()          # Riesgo ajustado
│   │   │       ├── get_current_state()          # Estado actual
│   │   │       └── _save/load_state()           # Persistencia
│   │   │
│   │   ├── performance_attribution.py # [v1.7+] Attribution de Performance
│   │   │   └── PerformanceAttribution
│   │   │       ├── record_trade()               # Registra trade
│   │   │       ├── get_attribution_by_agent()   # P&L por agente
│   │   │       ├── get_attribution_by_regime()  # P&L por régimen
│   │   │       ├── get_attribution_by_symbol()  # P&L por símbolo
│   │   │       ├── get_attribution_by_hour()    # P&L por hora
│   │   │       ├── get_full_attribution_report()# Reporte completo
│   │   │       └── get_recommendations()        # Recomendaciones
│   │   │
│   │   ├── position_store.py         # [v1.5+v1.7] Persistencia SQLite (thread-safe)
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

## Flujo de Datos Principal v1.7+

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CICLO DE TRADING v1.7+                               │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   main.py run() │
                              │  Loop cada 180s │
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
│  ┌─────────────────┐    ┌─────────────────┐                                 │
│  │  Market Engine  │───►│   Technical     │                                 │
│  │  get_ohlcv()    │    │   Analyzer      │                                 │
│  │  get_order_book │    │  RSI,MACD,EMA   │                                 │
│  └─────────────────┘    └─────────────────┘                                 │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FILTROS INSTITUCIONALES v1.7+ (PRE-IA)                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  1. CORRELATION FILTER                                               │    │
│  │     ├─ Posiciones abiertas: [BTC/USDT LONG]                         │    │
│  │     ├─ Quiere abrir: ETH/USDT LONG                                  │    │
│  │     ├─ Correlación BTC-ETH: 85%                                     │    │
│  │     └─ RESULTADO: ❌ BLOQUEADO (>70%) → Log InfluxDB                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│                                   ▼ (si pasa)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  2. MULTI-TIMEFRAME ANALYSIS                                         │    │
│  │     ├─ 4H: BULLISH (EMA50 > EMA200, RSI > 50)     [peso: 50%]       │    │
│  │     ├─ 1H: BULLISH (MACD > Signal)                [peso: 30%]       │    │
│  │     ├─ 15m: BULLISH (Precio > EMA200)             [peso: 20%]       │    │
│  │     ├─ Alignment Score: 85%                                         │    │
│  │     └─ RESULTADO: ✅ ALINEADO + Boost confianza +17% → Log InfluxDB │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ Solo si pasa filtros PRE-IA
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI ENGINE + MTF BOOST                           │
│                                                                              │
│  ┌─────────────────┐                                                        │
│  │   AI Engine     │    Confianza Base: 0.70                                │
│  │                 │    MTF Boost: +0.12 (17%)                              │
│  │ Nivel 0: Local  │    ─────────────────                                   │
│  │ Nivel 1: Fast   │    Confianza Final: 0.82                               │
│  │ Nivel 2: Deep   │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           └──────────────────────────────────────────────────────────────   │
│                                                                              │
│                                              COMPRA / VENTA / ESPERA        │
└─────────────────────────────────────────────────────────────────────────────┘
                                                          │
                               ┌──────────────────────────┘
                               │ SI: COMPRA o VENTA
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     VALIDACIÓN ADAPTATIVA v1.7+ (POST-IA)                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  3. ADAPTIVE PARAMETERS CHECK                                        │    │
│  │     ├─ Win Rate reciente (20 trades): 45%                           │    │
│  │     ├─ Loss Streak actual: 2                                        │    │
│  │     ├─ Volatilidad mercado: HIGH                                    │    │
│  │     ├─ Min Confidence ajustada: 0.70 (subió de 0.65)                │    │
│  │     └─ RESULTADO: ❌ Confianza 0.68 < 0.70 mínima                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│                                   ▼ (si pasa)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  4. RISK/REWARD VALIDATION                                           │    │
│  │     ├─ Entry: $100,000                                              │    │
│  │     ├─ SL: $98,000 (riesgo: $2,000)                                 │    │
│  │     ├─ TP: $103,000 (ganancia: $3,000)                              │    │
│  │     ├─ R/R Ratio: 1.5:1                                             │    │
│  │     └─ RESULTADO: ✅ R/R >= 1.5 mínimo (RECHAZA si < 1.5)           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ Solo si pasa TODOS los filtros
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Risk Manager                                    │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ validate_trade  │───►│ Kelly Criterion │───►│ Position Size   │          │
│  │ check_kill_sw.  │    │ (auto-update)   │    │ SL, TP calc     │          │
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
│                   POSITION MANAGEMENT SYSTEM v1.5 + v1.7+                    │
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
│  ┌────────────────────────────────────────────────────┐ │  │    │
│  │ v1.7+ CALLBACKS (ON POSITION CLOSE)                │ │  │    │
│  │                                                     │ │  │    │
│  │  • Kelly Criterion auto-update                     │ │  │    │
│  │  • Institutional Metrics (Sharpe, Sortino, etc)    │ │  │    │
│  │  • Performance Attribution (por agente/régimen)    │ │  │    │
│  │  • Adaptive Parameters update (win/loss streak)    │ │  │    │
│  │  • InfluxDB logging (todas las métricas)           │ │  │    │
│  └────────────────────────────────────────────────────┘ │  │    │
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

## Dependencias entre Módulos v1.7+

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GRAFO DE DEPENDENCIAS v1.7+                           │
└─────────────────────────────────────────────────────────────────────────────┘

                                    main.py
                                       │
     ┌─────────────────┬───────────────┼───────────────┬──────────────────┐
     │                 │               │               │                  │
     ▼                 ▼               ▼               ▼                  ▼
┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌────────────────┐
│ AIEngine  │   │ Market    │   │ Risk      │   │ Position  │   │ v1.7+ FILTERS  │
│           │   │ Engine    │   │ Manager   │   │ Engine    │   │                │
└─────┬─────┘   └─────┬─────┘   └───────────┘   └─────┬─────┘   │ MTF Analyzer   │
      │               │                               │         │ Correlation    │
      │               │                               │         │ Adaptive Params│
      ▼               │                               │         │ Attribution    │
┌───────────┐         │                               │         └────────────────┘
│ Technical │         │                               │
│ Analyzer  │◄────────┘                               │
└───────────┘                                         │
      │                                               │
      │ (volatility_level)                            │
      ▼                                               │
┌───────────┐                                         │
│ Adaptive  │◄────────────────────────────────────────┤ (on position close)
│ Params    │                                         │
└───────────┘                                         │
                                                      │
              ┌───────────────────────────────────────┤
              │                                       │
              ▼                                       ▼
        ┌───────────┐                          ┌───────────────┐
        │ Order     │                          │ Performance   │
        │ Manager   │                          │ Attribution   │
        └─────┬─────┘                          └───────────────┘
              │
              ▼
        ┌───────────┐
        │ Exchange  │
        │ (CCXT)    │
        └───────────┘

        ─────────────────────────────────────────────────

                      Data Logger (InfluxDB)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  ┌───────────┐        ┌───────────┐        ┌───────────────────┐
  │ Trade     │        │ MTF       │        │ v1.7+ Metrics     │
  │ Results   │        │ Analysis  │        │ Correlation       │
  │           │        │           │        │ Adaptive Params   │
  └───────────┘        └───────────┘        │ Attribution       │
                                            └───────────────────┘

        ─────────────────────────────────────────────────

                      Grafana Dashboard
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  ┌───────────┐        ┌───────────┐        ┌───────────────────┐
  │ Métricas  │        │ Filtros   │        │ Attribution       │
  │ Básicas   │        │ v1.7+     │        │ Analysis          │
  │ PnL, Win% │        │ MTF Score │        │ P&L por Agente    │
  │ Trades    │        │ Div Score │        │ Win Rate Régimen  │
  └───────────┘        └───────────┘        └───────────────────┘
```

## Flujo de Callbacks al Cerrar Posición

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   CALLBACKS ON POSITION CLOSE (v1.7+)                        │
└─────────────────────────────────────────────────────────────────────────────┘

                        Position Closed
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │           _record_institutional_metrics()    │
        └──────────────────────┬──────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌────────────┐       ┌────────────┐      ┌────────────┐
   │ Kelly      │       │ Instit.    │      │ DataLogger │
   │ Criterion  │       │ Metrics    │      │ (InfluxDB) │
   │ Update     │       │ Record     │      │            │
   └────────────┘       └────────────┘      └────────────┘
          │
          ▼
   ┌────────────────────────────────────────────────────┐
   │              _record_performance_attribution()      │
   └──────────────────────┬─────────────────────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │ Perf.      │
                   │ Attribution│
                   │ Record     │
                   └────────────┘
          │
          ▼
   ┌────────────────────────────────────────────────────┐
   │              _update_adaptive_params()              │
   └──────────────────────┬─────────────────────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │ Adaptive   │
                   │ Manager    │
                   │ Update     │
                   └────────────┘
```

---

**Última actualización**: Diciembre 2025 - v1.8.1 INSTITUCIONAL PRO ★★★★★
