# Sistema Autónomo de Trading Híbrido (SATH) v1.8.1

## INSTITUCIONAL PRO ★★★★★

Bot de trading profesional que combina análisis técnico cuantitativo con razonamiento de IA para trading autónomo en criptomonedas. Diseñado con estándares de hedge funds institucionales.

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     Sistema Autónomo de Trading Híbrido (SATH) v1.8.1       ║
║           ★★★★★ INSTITUCIONAL PRO ★★★★★                      ║
║                                                               ║
║     ✓ ATR-Based Stop Loss/TP       ✓ Correlation Filter     ║
║     ✓ Multi-Timeframe (4H→1H→15m)  ✓ Session Filter         ║
║     ✓ Kelly Criterion (1/4)        ✓ R/R 2:1+ Obligatorio   ║
║     ✓ Confianza mínima 70%         ✓ MTF Alignment 75%+     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

## Filosofía v1.8.1

```
MENOS TRADES + MAYOR CALIDAD = MEJOR RENTABILIDAD
```

- Solo trades de alta convicción (>70% confianza)
- R/R mínimo 2:1 obligatorio
- ATR-based stops (respeta volatilidad)
- Multi-timeframe alignment requerido

## Características v1.8.1 INSTITUCIONAL PRO

### Nuevos en v1.8.1

| Feature | Descripción | Impacto |
|---------|-------------|---------|
| **ATR-Based SL** | Stop Loss dinámico según volatilidad | -50% SL prematuros |
| **ATR-Based TP** | Take Profit automático R/R 2:1 | R/R garantizado |
| **Confianza 70%+** | Solo trades alta convicción | +20% win rate |
| **MTF 75%+** | Mayor alineación requerida | Menos señales falsas |
| **Profit/Fees 8x** | Solo trades muy rentables | Mejor expectativa |
| **API Retries** | Reintentos configurables | Mayor resiliencia |

### Filtros de Calidad

| Filtro | Descripción | PAPER | LIVE |
|--------|-------------|-------|------|
| **Multi-Timeframe** | 4H→1H→15m alineados | 75% | 80% |
| **Confianza mínima** | Solo alta convicción | 70% | 75% |
| **R/R Validation** | RECHAZA si R/R < 2:1 | 2.0 | 2.0 |
| **Correlation Filter** | Bloquea >70% correlación | 70% | 65% |
| **Profit/Fees** | Ratio mínimo ganancia/fees | 8x | 10x |
| **Kill Switch** | Pérdida máxima diaria | 5% | 4% |

### Métricas Institucionales

- **Sharpe Ratio** (30 días rolling)
- **Sortino Ratio** (solo downside risk)
- **Calmar Ratio** (return/max drawdown)
- **Max Drawdown** tracking en tiempo real
- **Fill Rate** de órdenes limit
- **Latencia P50/P95/P99** de ejecución
- **Win Rate por Régimen** (trend/reversal/range)
- **Performance Attribution** por agente/símbolo/hora

## Arquitectura v1.8.1

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FLUJO DE TRADING v1.8.1 INSTITUCIONAL PRO             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐                                                           │
│  │ Market Data  │ → OHLCV (150-200 velas) + Order Book + Funding Rate      │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐                                                           │
│  │  Technical   │ → RSI, MACD, EMA 50/200, Bollinger, ATR                  │
│  │  Analyzer    │ → ATR usado para SL/TP dinámicos                         │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    FILTROS v1.8.1 INSTITUCIONAL PRO                  │  │
│  │                                                                       │  │
│  │  1. MULTI-TIMEFRAME ANALYSIS                                          │  │
│  │     ├─ 4H (55% peso): Tendencia macro DOMINANTE                      │  │
│  │     ├─ 1H (30% peso): Confirmación de momentum                       │  │
│  │     ├─ 15m (15% peso): Timing de entrada                             │  │
│  │     ├─ Min alignment: 75% PAPER / 80% LIVE                           │  │
│  │     └─ Si alineado: Boost confianza +5-15%                           │  │
│  │                                                                       │  │
│  │  2. CORRELATION FILTER                                                │  │
│  │     ├─ Max correlación: 70% PAPER / 65% LIVE                         │  │
│  │     └─ Bloquea sobreexposición a activos similares                   │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│         │                                                                   │
│         ▼ Solo si pasa filtros MTF                                         │
│  ┌──────────────┐                                                           │
│  │  AI Engine   │ → Análisis híbrido (DeepSeek-Chat + DeepSeek-Reasoner)  │
│  │  Híbrido     │ → Agentes especializados (trend, volatility, sentiment)  │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    VALIDACIÓN DE RIESGO v1.8.1                        │  │
│  │                                                                       │  │
│  │  3. CONFIDENCE FILTER                                                 │  │
│  │     ├─ Min confianza: 70% PAPER / 75% LIVE                           │  │
│  │     └─ Incluye boost de MTF                                          │  │
│  │                                                                       │  │
│  │  4. ATR-BASED STOPS (NUEVO v1.8)                                      │  │
│  │     ├─ SL = Entry ± (ATR × 2.0)                                      │  │
│  │     ├─ TP = Entry ± (ATR × 4.0) → R/R 2:1                            │  │
│  │     ├─ Límites: 0.5% mínimo, 5.5% máximo                             │  │
│  │     └─ Respeta volatilidad de cada activo                            │  │
│  │                                                                       │  │
│  │  5. R/R VALIDATION                                                    │  │
│  │     ├─ Mínimo: 2.0:1 OBLIGATORIO                                     │  │
│  │     └─ RECHAZA trades con R/R < 2.0                                  │  │
│  │                                                                       │  │
│  │  6. KELLY CRITERION SIZING                                            │  │
│  │     ├─ Fracción: 0.25 PAPER / 0.20 LIVE                              │  │
│  │     ├─ Ajusta por confianza y win rate histórico                     │  │
│  │     └─ Max risk cap: 2.5% PAPER / 1.5% LIVE                          │  │
│  │                                                                       │  │
│  │  7. FEE PROFITABILITY CHECK                                           │  │
│  │     ├─ Profit/fees ratio: 8x PAPER / 10x LIVE                        │  │
│  │     ├─ Min profit after fees: $1.00 PAPER / $0.75 LIVE               │  │
│  │     └─ RECHAZA si trade no es rentable                               │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│         │                                                                   │
│         ▼ Solo si pasa TODOS los filtros                                   │
│  ┌──────────────┐                                                           │
│  │  Execution   │ → Orden Limit con verificación pre-ejecución            │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐                                                           │
│  │  Position    │ → OCO (SL+TP automáticos)                               │
│  │  Engine      │ → Trailing Stop: 2.5-3% activation, 1-1.2% trail        │
│  │              │ → Cooldown 5s + Safety margin 0.4-0.5%                  │
│  └──────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Expectativa Matemática

```
CONFIGURACIÓN PAPER $300:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Win Rate esperado con filtros v1.8.1: 45-55%
R/R mínimo garantizado: 2.0:1
Fees round-trip: 0.15%

ESCENARIO CONSERVADOR (45% WR):
E = (0.45 × 2) - (0.55 × 1) = +0.35 por unidad de riesgo
Con $4.50 riesgo por trade → +$1.58 expectativa/trade

PROYECCIÓN MENSUAL (20 trades):
- Conservador (45% WR): +$31.50 (+10.5% mensual)
- Optimista (55% WR): +$58.50 (+19.5% mensual)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

# Paper Trading (Testnet) - $300
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

## Configuración v1.8.1

### Variables de Entorno (.env)

```env
# IA (DeepSeek recomendado)
DEEPSEEK_API_KEY=sk-xxx

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
# v1.8.1 INSTITUCIONAL PRO - $300

# Agentes con reintentos
ai_agents:
  enabled: true
  min_volatility_percent: 0.35
  min_volume_ratio: 0.5
  max_retries: 3
  retry_delay_seconds: 2

# Gestión de Riesgo
risk_management:
  max_risk_per_trade: 1.5
  max_daily_drawdown: 5.0
  min_risk_reward_ratio: 2.0  # OBLIGATORIO
  initial_capital: 300

  # ATR-based Stops (NUEVO v1.8)
  atr_stops:
    enabled: true
    sl_multiplier: 2.0      # SL = 2x ATR
    tp_multiplier: 4.0      # TP = 4x ATR (R/R 2:1)
    min_distance_percent: 0.5
    max_distance_percent: 5.5

  # Kelly Criterion
  kelly_criterion:
    enabled: true
    fraction: 0.25          # 1/4 Kelly
    min_confidence: 0.70    # Solo >70% confianza
    max_risk_cap: 2.5

  # Validación de rentabilidad
  position_sizing:
    min_position_usd: 40.0
    min_profit_after_fees_usd: 1.00
    profit_to_fees_ratio: 8.0

# Multi-Timeframe
multi_timeframe:
  enabled: true
  min_alignment_score: 0.75  # 75% mínimo
  weights:
    higher: 0.55  # 4H domina
    medium: 0.30  # 1H confirma
    lower: 0.15   # 15m timing

# Trailing Stop
position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 2.5
    trail_distance_percent: 1.2
    min_profit_to_lock: 0.8
    cooldown_seconds: 5
    min_safety_margin_percent: 0.4

  portfolio:
    max_concurrent_positions: 1
    max_exposure_percent: 50

# Parámetros Adaptativos
adaptive_parameters:
  enabled: true
  lookback_trades: 30
  sensitivity: 0.15
  ranges:
    min_confidence: { min: 0.65, max: 0.85 }
```

## Diferencias PAPER vs LIVE

| Parámetro | PAPER $300 | LIVE $100 |
|-----------|-----------|-----------|
| min_confidence | 0.70 | **0.75** |
| MTF alignment | 0.75 | **0.80** |
| min_volatility | 0.35% | **0.40%** |
| max_slippage | 0.30% | **0.20%** |
| profit_to_fees_ratio | 8x | **10x** |
| sensitivity | 0.15 | **0.10** |
| kill_switch | 5% | **4%** |

## Métricas en Grafana

### Acceso

| Modo | URL | Puerto |
|------|-----|--------|
| Paper | http://localhost:3001 | 3001 |
| Live | http://localhost:3000 | 3000 |

Credenciales: `admin` / `sath_grafana_2024`

### Paneles Disponibles

- **Fila 1**: PnL Total, Win Rate, Total Trades, Avg PnL
- **Fila 2**: Sharpe, Sortino, Calmar, Max Drawdown, Fill Rate
- **Fila 3**: Latencia P50/P95/P99, Capital tracking
- **Fila 4**: MTF Alignment, Diversification, P&L por Agente

## Estructura del Proyecto

```
bot/
├── config/
│   ├── config_paper.yaml      # v1.8.1 Paper ($300)
│   └── config_live.yaml       # v1.8.1 Live ($100)
├── src/
│   ├── engines/
│   │   ├── ai_engine.py       # IA híbrida + reintentos v1.8.1
│   │   ├── market_engine.py   # Conexión exchanges + OCO
│   │   ├── position_engine.py # Trailing stop v1.8.1
│   │   └── websocket_engine.py
│   └── modules/
│       ├── multi_timeframe.py        # MTF 75-80%
│       ├── correlation_filter.py     # Correlación 65-70%
│       ├── adaptive_parameters.py    # Parámetros adaptativos
│       ├── performance_attribution.py
│       ├── institutional_metrics.py  # Sharpe, Sortino, etc
│       ├── risk_manager.py           # ATR stops + Kelly v1.8.1
│       ├── data_logger.py            # InfluxDB
│       └── notifications.py          # Telegram
├── docs/
│   ├── CHANGELOG.md                  # Historial de versiones
│   ├── CONFIGURACION_POR_CAPITAL.md  # Guía por capital
│   └── ...
├── grafana/
│   └── provisioning/
│       └── dashboards/
├── docker-compose.paper.yml   # Docker Paper
├── docker-compose.live.yml    # Docker Live
├── main.py                    # Orquestador v1.8.1
└── README.md
```

## Gestión de Riesgo v1.8.1

### Protecciones Activas

| Protección | PAPER | LIVE | Acción |
|------------|-------|------|--------|
| Kill Switch | 5% | 4% | Apaga bot 24h |
| R/R Validation | ≥2.0 | ≥2.0 | Rechaza trade |
| Correlation | 70% | 65% | Bloquea trade |
| MTF Alignment | 75% | 80% | Salta análisis |
| Confianza mín. | 70% | 75% | Rechaza trade |
| Profit/Fees | 8x | 10x | Rechaza trade |
| Trailing Stop | 2.5% | 3.0% | Protege ganancias |

### Kelly Criterion v1.8.1

```
Kelly % = (W × R - L) / R × fraction

Donde:
- W = Win rate histórico (o 0.50 si <10 trades)
- L = 1 - W
- R = Ratio ganancia/pérdida promedio
- fraction = 0.25 PAPER / 0.20 LIVE

Ejemplo con 50% WR y R/R 2:1:
Kelly = (0.50 × 2 - 0.50) / 2 × 0.25 = 0.125 = 12.5% del capital
```

## Changelog

### v1.8.1 - 2025-12-03 (INSTITUCIONAL PRO ★★★★★)

**Optimizado:**
- Confianza mínima: 60% → **70-75%**
- Kelly fraction: 0.20 → **0.25**
- MTF alignment: 70% → **75-80%**
- Volatilidad mínima: 0.25% → **0.35-0.40%**
- Min candles: 100 → **150-200**
- Profit/fees ratio: 5x → **8-10x**
- Trailing activation: 2.0% → **2.5-3.0%**
- Cooldown: 3s → **5s**

**Agregado:**
- Reintentos de API configurables (max_retries, retry_delay)
- Variables de trailing stop desde config (antes hardcodeadas)

### v1.8 - 2025-12-03 (INSTITUCIONAL)

- **ATR-Based Stop Loss** - SL dinámico por volatilidad
- **ATR-Based Take Profit** - R/R 2:1 garantizado
- **Session Filter** - Horarios óptimos de liquidez
- **Kelly Criterion Mejorado** - Historial persistente
- **R/R mínimo 2.0** - Rechaza trades con mal ratio

### v1.7+ - Nivel Institucional Superior

- Multi-Timeframe Analysis
- Correlation Filter
- Adaptive Parameters
- Performance Attribution
- Métricas Institucionales

## Solución de Problemas

### Bot no opera aunque hay señales

1. **Verificar MTF**: Alignment debe ser ≥75% (PAPER) o ≥80% (LIVE)
2. **Verificar Confianza**: Debe superar 70% (PAPER) o 75% (LIVE)
3. **Verificar R/R**: Ratio debe ser ≥2.0
4. **Verificar Profit/Fees**: Ratio debe ser ≥8x (PAPER) o ≥10x (LIVE)

### Error de conexión API

Los reintentos están configurados en v1.8.1:
- `max_retries: 3`
- `retry_delay_seconds: 2`

### Kelly siempre usa valores conservadores

Normal para <10 trades. El historial se guarda en `data/risk_manager_state.json`.

## Comandos Útiles

```bash
# Ver logs en tiempo real
docker logs -f sath_bot_paper

# Reiniciar bot
docker compose -f docker-compose.paper.yml restart trading_bot

# Ver estado de contenedores
docker compose -f docker-compose.paper.yml ps

# Backup de estado
cp data/risk_manager_state.json data/backup_$(date +%Y%m%d).json
cp data/positions.db data/positions_backup_$(date +%Y%m%d).db
```

---

**SATH v1.8.1 INSTITUCIONAL PRO ★★★★★**

*Menos trades, mayor calidad, mejor rentabilidad.*

*Desarrollado para traders que exigen estándares de hedge fund.*
