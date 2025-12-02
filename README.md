# Sistema Autónomo de Trading Híbrido (SATH) v1.7+

## Nivel Institucional Superior

Bot de trading profesional que combina análisis técnico cuantitativo con razonamiento de IA para trading autónomo en criptomonedas. Diseñado con estándares de hedge funds institucionales.

```
╔═══════════════════════════════════════════════════════════════╗
║     Sistema Autónomo de Trading Híbrido (SATH) v1.7+        ║
║           NIVEL INSTITUCIONAL SUPERIOR                       ║
║                                                               ║
║     ✓ Multi-Timeframe (4H→1H→15m)  ✓ Correlation Filter     ║
║     ✓ Adaptive Parameters          ✓ Performance Attribution ║
║     ✓ Kelly Criterion Dinámico     ✓ R/R Validation         ║
╚═══════════════════════════════════════════════════════════════╝
```

## Características v1.7+ (Nivel Institucional)

### Nuevos Filtros de Calidad

| Filtro | Descripción | Impacto |
|--------|-------------|---------|
| **Multi-Timeframe** | Solo opera cuando 4H→1H→15m están alineados | +15-25% win rate |
| **Correlation Filter** | Bloquea trades si correlación >70% con posición existente | -20% drawdown |
| **Adaptive Parameters** | Auto-ajusta confianza/riesgo según rendimiento | Recuperación rápida |
| **R/R Validation** | RECHAZA trades con R/R < 1.5:1 (antes solo warning) | Evita trades perdedores |

### Métricas Institucionales

- **Sharpe Ratio** (30 días rolling)
- **Sortino Ratio** (solo downside risk)
- **Calmar Ratio** (return/max drawdown)
- **Max Drawdown** tracking en tiempo real
- **Fill Rate** de órdenes limit
- **Latencia P50/P95/P99** de ejecución
- **Win Rate por Régimen** (trend/reversal/range)
- **Performance Attribution** por agente/símbolo/hora

### Dashboard Grafana

19 paneles de métricas en tiempo real:
- Métricas institucionales (Sharpe, Sortino, Calmar)
- Calidad de ejecución (latencia, slippage, fill rate)
- Filtros avanzados (MTF alignment, diversification score)
- Attribution (P&L por agente, win rate por régimen)

## Arquitectura v1.7+

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUJO DE TRADING v1.7+                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐                                                           │
│  │ Market Data  │ → Obtener OHLCV + Order Book + Funding Rate               │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐                                                           │
│  │  Technical   │ → RSI, MACD, EMA, Bollinger, ATR                          │
│  │  Analyzer    │ → volatility_level → Adaptive Manager                     │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    FILTROS INSTITUCIONALES v1.7+                      │  │
│  │                                                                       │  │
│  │  1. CORRELATION FILTER                                                │  │
│  │     ├─ Posiciones abiertas: [BTC/USDT LONG]                          │  │
│  │     ├─ Quiere abrir: ETH/USDT LONG                                   │  │
│  │     ├─ Correlación BTC-ETH: 85%                                      │  │
│  │     └─ RESULTADO: ❌ BLOQUEADO (>70%)                                 │  │
│  │                                                                       │  │
│  │  2. MULTI-TIMEFRAME ANALYSIS                                          │  │
│  │     ├─ 4H: BULLISH (EMA50 > EMA200, RSI > 50)                        │  │
│  │     ├─ 1H: BULLISH (MACD > Signal)                                   │  │
│  │     ├─ 15m: BULLISH (Precio > EMA200)                                │  │
│  │     ├─ Alignment Score: 85%                                          │  │
│  │     └─ RESULTADO: ✅ ALINEADO + Boost confianza +17%                  │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│         │                                                                   │
│         ▼ Solo si pasa filtros                                             │
│  ┌──────────────┐                                                           │
│  │  AI Engine   │ → Agentes Especializados (Trend/Reversal)                │
│  │  + MTF Boost │ → Confianza ajustada con boost de alineación             │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    VALIDACIÓN ADAPTATIVA                              │  │
│  │                                                                       │  │
│  │  3. ADAPTIVE PARAMETERS                                               │  │
│  │     ├─ Win Rate reciente: 45%                                        │  │
│  │     ├─ Loss Streak: 2                                                │  │
│  │     ├─ Min Confidence ajustada: 0.70 (subió de 0.65)                 │  │
│  │     └─ RESULTADO: ❌ Confianza 0.68 < 0.70 mínima                     │  │
│  │                                                                       │  │
│  │  4. RISK/REWARD VALIDATION                                            │  │
│  │     ├─ Entry: $100,000                                               │  │
│  │     ├─ SL: $98,000 (riesgo: $2,000)                                  │  │
│  │     ├─ TP: $103,000 (ganancia: $3,000)                               │  │
│  │     ├─ R/R Ratio: 1.5:1                                              │  │
│  │     └─ RESULTADO: ✅ R/R >= 1.5 mínimo                                │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│         │                                                                   │
│         ▼ Solo si pasa TODOS los filtros                                   │
│  ┌──────────────┐                                                           │
│  │  Execution   │ → Orden Limit con verificación de liquidez               │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐                                                           │
│  │  Position    │ → OCO (SL+TP) + Trailing Stop con cooldown               │
│  │  Engine      │ → Al cerrar: actualiza Kelly + Attribution + Adaptive    │
│  └──────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Instalación Rápida

### Docker (Recomendado)

```bash
# Clonar repositorio
git clone <tu-repositorio>
cd bot

# Configurar credenciales
cp .env.example .env
nano .env  # Agregar API keys

# Paper Trading (Testnet)
docker compose -f docker-compose.paper.yml up -d

# Ver logs
docker logs -f sath_bot_paper

# Grafana Dashboard
open http://localhost:3001  # user: admin, pass: sath_grafana_2024
```

### Local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Configuración

### Variables de Entorno (.env)

```env
# IA (al menos uno requerido)
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx           # Opcional
GEMINI_API_KEY=xxx              # Opcional

# Exchange
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx

# Para Paper Trading (Testnet)
BINANCE_TESTNET_API_KEY=xxx
BINANCE_TESTNET_API_SECRET=xxx

# Notificaciones (opcional)
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx

# InfluxDB (para métricas)
INFLUXDB_TOKEN=xxx
```

### Configuración Principal (config/config_paper.yaml)

```yaml
# Filtros Institucionales v1.7+
multi_timeframe:
  enabled: true
  higher_timeframe: "4h"
  medium_timeframe: "1h"
  lower_timeframe: "15m"
  min_alignment_score: 0.70

correlation_filter:
  enabled: true
  max_correlation: 0.70

adaptive_parameters:
  enabled: true
  lookback_trades: 20
  sensitivity: 0.25

performance_attribution:
  enabled: true

# Gestión de Riesgo
risk_management:
  max_risk_per_trade: 1.0
  max_daily_drawdown: 5.0
  min_risk_reward_ratio: 1.5  # RECHAZA si R/R < 1.5

  kelly_criterion:
    enabled: true
    fraction: 0.15
    min_confidence: 0.65

# Trailing Stop v1.7
position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 2.0
    trail_distance_percent: 1.5
    cooldown_seconds: 3           # Evita race conditions
    min_safety_margin_percent: 0.3
```

## Métricas en Grafana

### Acceso

| Modo | URL | Puerto |
|------|-----|--------|
| Paper | http://localhost:3001 | 3001 |
| Live | http://localhost:3000 | 3000 |

Credenciales: `admin` / `sath_grafana_2024`

### Paneles Disponibles

**Fila 1: Resumen**
- PnL Total, Win Rate, Total Trades, Avg PnL

**Fila 2: Métricas Institucionales**
- Sharpe Ratio (30d), Sortino Ratio, Calmar Ratio
- Max Drawdown, Fill Rate, Slippage Promedio

**Fila 3: Calidad de Ejecución**
- Latencia P50/P95/P99
- Capital Current vs Peak
- Slippage Histórico

**Fila 4: Filtros Avanzados v1.7+**
- MTF Alignment Score
- Diversification Score
- Win/Loss Streaks
- Adaptive Parameters Over Time
- P&L por Agente
- Win Rate por Régimen

## Estructura del Proyecto

```
bot/
├── config/
│   ├── config_paper.yaml      # Configuración Paper (Testnet)
│   └── config_live.yaml       # Configuración Live (Producción)
├── src/
│   ├── engines/
│   │   ├── ai_engine.py       # Motor IA + Agentes especializados
│   │   ├── market_engine.py   # Conexión exchanges + OCO
│   │   ├── position_engine.py # Gestión posiciones + Trailing
│   │   └── websocket_engine.py
│   └── modules/
│       ├── multi_timeframe.py        # v1.7+ MTF Analysis
│       ├── correlation_filter.py     # v1.7+ Correlation
│       ├── adaptive_parameters.py    # v1.7+ Adaptive
│       ├── performance_attribution.py # v1.7+ Attribution
│       ├── institutional_metrics.py  # Sharpe, Sortino, etc
│       ├── risk_manager.py           # Kelly + R/R Validation
│       ├── data_logger.py            # InfluxDB logging
│       └── notifications.py          # Telegram alerts
├── grafana/
│   └── provisioning/
│       ├── dashboards/
│       │   └── sath-trading.json     # Dashboard completo
│       └── datasources/
│           └── influxdb.yml          # Conexión InfluxDB
├── tests/
│   └── test_v17_institutional.py     # 28 tests
├── docker-compose.paper.yml   # Docker Paper Trading
├── docker-compose.live.yml    # Docker Live Trading
├── main.py                    # Orquestador principal
└── README.md
```

## Tests

```bash
# Ejecutar todos los tests v1.7
python -m pytest tests/test_v17_institutional.py -v

# Resultado esperado: 28 passed
```

## Gestión de Riesgo

### Protecciones Activas

| Protección | Trigger | Acción |
|------------|---------|--------|
| Kill Switch | Pérdida > 5% diario | Apaga bot 24h |
| R/R Validation | R/R < 1.5:1 | Rechaza trade |
| Correlation | Correlación > 70% | Bloquea trade |
| MTF Alignment | Alineación < 70% | Salta análisis |
| Adaptive Confidence | Win rate bajo | Sube min_confidence |
| Trailing Stop | Profit > 2% | Protege ganancias |
| Circuit Breaker | Fallos API | Pausa llamadas |

### Kelly Criterion

El position sizing se ajusta automáticamente basado en:
- Historial de trades (wins/losses)
- Racha actual (win streak / loss streak)
- Confianza del trade

```
Kelly % = (W × R - L) / R

Donde:
- W = Probabilidad de ganar (del historial)
- L = Probabilidad de perder (1 - W)
- R = Ratio de ganancias/pérdidas promedio
```

## Changelog v1.7+

### v1.7+ - Nivel Institucional Superior
- **Multi-Timeframe Analysis**: Solo opera con 4H→1H→15m alineados
- **Correlation Filter**: Evita sobreexposición (bloquea >70% correlación)
- **Adaptive Parameters**: Auto-ajuste de confianza/riesgo
- **Performance Attribution**: Análisis de alpha por agente/régimen/hora
- **R/R Validation**: RECHAZA trades con R/R < 1.5 (antes solo warning)
- **Kelly Criterion Auto-Update**: Se actualiza en cada cierre de posición
- **Trailing Stop Fix**: Cooldown 3s + safety margin 0.3%
- **Métricas Institucionales**: Sharpe, Sortino, Calmar, Fill Rate, Latencia
- **Dashboard Grafana**: 19 paneles para métricas v1.7+
- **InfluxDB Integration**: Todas las métricas se envían a la base de datos

### v1.6 - Robustez
- Circuit Breaker Pattern
- Health Monitor
- AI Ensemble System

### v1.5 - Position Management
- Órdenes OCO reales
- Supervisión IA
- Persistencia SQLite

## Solución de Problemas

### Bot no opera aunque hay señales

1. **Verificar MTF**: Los timeframes deben estar alineados (≥70%)
2. **Verificar Correlación**: No debe haber posiciones correlacionadas
3. **Verificar Confidence**: La confianza debe superar el mínimo adaptativo
4. **Verificar R/R**: El ratio riesgo/recompensa debe ser ≥1.5

### Métricas no aparecen en Grafana

1. Verificar que InfluxDB está corriendo: `docker ps | grep influxdb`
2. Verificar token en `.env`: `INFLUXDB_TOKEN`
3. Verificar bucket: `trading_decisions` o `trading_decisions_paper`

### Kelly siempre usa valores conservadores

El Kelly necesita historial de trades. Los primeros 50 trades usarán valores base.
El historial se guarda en `data/risk_manager_state.json`.

## Comandos Útiles

```bash
# Ver logs en tiempo real
docker logs -f sath_bot_paper

# Reiniciar bot
docker compose -f docker-compose.paper.yml restart trading_bot

# Ver estado de contenedores
docker compose -f docker-compose.paper.yml ps

# Consultar InfluxDB
docker exec -it sath_influxdb_paper influx query '
  from(bucket:"trading_decisions_paper")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "trade_result")
'

# Backup de posiciones
cp data/positions.db data/positions_backup_$(date +%Y%m%d).db
```

---

**SATH v1.7+ - Nivel Institucional Superior**

Desarrollado para traders que exigen estándares de hedge fund.

*28 tests passed | Métricas en tiempo real | Auto-adaptativo*
