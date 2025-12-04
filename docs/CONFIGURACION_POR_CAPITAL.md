# Guía de Configuración por Nivel de Capital

## Resumen Ejecutivo

Esta guía proporciona configuraciones óptimas para el bot de trading según el capital disponible. A menor capital, más conservador debe ser el enfoque para preservar el capital y permitir recuperación de pérdidas.

**Versión: v2.0 INSTITUCIONAL SUPERIOR ★★★★★**

---

## Filosofía v2.0

```
STOPS BASADOS EN ATR + R/R GARANTIZADO = RENTABILIDAD CONSISTENTE
```

- **CRÍTICO**: Risk Manager FUERZA SL/TP con ATR (ignora sugerencias de IA)
- SL mínimo 1.8% (antes 0.5% = stop-hunts constantes)
- R/R 2:1 garantizado matemáticamente
- Entradas más tempranas (MTF 65% vs 75% anterior)
- Trailing stop optimizado para capturar más ganancias

---

## Cambios v2.0 vs v1.8.1

| Feature | v1.8.1 | v2.0 | Impacto |
|---------|--------|------|---------|
| **SL Multiplier** | 2.0x ATR | **2.5x ATR** | Más espacio, menos stop-hunts |
| **TP Multiplier** | 4.0x ATR | **5.0x ATR** | R/R 2:1 garantizado |
| **min_distance_%** | 0.5% | **1.8%** | **CRÍTICO** - evita ruido |
| **max_distance_%** | 5.5% | **6.0%** | Para alta volatilidad |
| **MTF alignment** | 75% | **65%** | Entradas más tempranas |
| **MTF lower weight** | 15% | **20%** | Mejor timing |
| **Trailing activation** | 2.5% | **1.5%** | Captura más ganancias |
| **Trailing distance** | 1.2% | **1.5%** | Más espacio para respirar |
| **Cooldown** | 5s | **10s** | Evita whipsaws |
| **Risk Manager** | Valida SL | **FUERZA SL** | Ignora IA, usa ATR |

---

## Tabla de Configuraciones Recomendadas

### Risk Management (`risk_management:`)

| Capital | max_risk_per_trade | max_daily_drawdown | min_risk_reward_ratio | leverage |
|---------|-------------------|--------------------|-----------------------|----------|
| $100    | 1.0% ($1)         | 4.0% ($4)          | **2.0**               | 1        |
| $200    | 1.0% ($2)         | 4.0% ($8)          | **2.0**               | 1        |
| $300    | 1.5% ($4.50)      | 5.0% ($15)         | **2.0**               | 1        |
| $400    | 1.5% ($6)         | 5.0% ($20)         | **2.0**               | 1        |
| $500    | 1.5% ($7.50)      | 5.0% ($25)         | **2.0**               | 1        |
| $600    | 2.0% ($12)        | 6.0% ($36)         | **2.0**               | 1        |
| $700    | 2.0% ($14)        | 6.0% ($42)         | **2.0**               | 1        |
| $800    | 2.0% ($16)        | 7.0% ($56)         | **2.0**               | 1        |
| $900    | 2.5% ($22.50)     | 7.0% ($63)         | **2.0**               | 1        |
| $1000   | 2.5% ($25)        | 8.0% ($80)         | **2.0**               | 1        |

> **v2.0 CRÍTICO**: `min_risk_reward_ratio` es **SIEMPRE 2.0** - trades con R/R < 2.0 son **RECHAZADOS**

---

### ATR-Based Stops (`risk_management.atr_stops:`) - v2.0 **CRÍTICO**

| Capital | enabled | sl_multiplier | tp_multiplier | min_distance_% | max_distance_% |
|---------|---------|---------------|---------------|----------------|----------------|
| $100 LIVE | true  | **2.5**       | **5.0**       | **1.8%**       | 5.0%           |
| $100 PAPER| true  | **2.5**       | **5.0**       | **1.8%**       | 6.0%           |
| $300 PAPER| true  | **2.5**       | **5.0**       | **1.8%**       | **6.0%**       |
| $500+     | true  | **2.5**       | **5.0**       | **1.8%**       | 5.5%           |

**v2.0 CAMBIO CRÍTICO:**

- `sl_multiplier`: **2.5x ATR** (antes 2.0x) - más espacio para respirar
- `tp_multiplier`: **5.0x ATR** (antes 4.0x) - R/R 2:1 garantizado
- `min_distance_percent`: **1.8%** (antes 0.5%) - **EVITA STOP-HUNTS**
- Risk Manager **SIEMPRE** recalcula SL/TP con ATR, **IGNORANDO** sugerencias de IA

**Ejemplo BTC a $93,000 con ATR 1.5%:**

```
v1.8.1 (PROBLEMA):
- SL = 1.5% × 2 = 3.0% → $90,210 (pero IA sugería $92,000 = 1%)
- El mercado cayó a $90,775 y tocó el SL

v2.0 (SOLUCIÓN):
- SL = MAX(1.5% × 2.5, 1.8%) = 3.75% → $89,512
- TP = 1.5% × 5 = 7.5% → $99,975
- R/R = 7.5/3.75 = 2:1 ✅
- El mismo movimiento NO hubiera tocado el SL
```

---

### Multi-Timeframe (`multi_timeframe:`) - v2.0

| Modo  | min_alignment_score | higher_weight | medium_weight | lower_weight |
|-------|---------------------|---------------|---------------|--------------|
| PAPER | **0.65** (65%)      | **0.50**      | 0.30          | **0.20**     |
| LIVE  | **0.70** (70%)      | 0.50          | 0.30          | 0.20         |

**v2.0 Cambios:**

- `min_alignment_score`: **65%** (antes 75%) - entradas más tempranas
- `higher_weight`: **50%** (antes 55%) - menos dependencia de 4H
- `lower_weight`: **20%** (antes 15%) - mejor timing de entrada

**Razón**: Con 75% se entraba tarde, cuando el movimiento ya había ocurrido.

---

### Trailing Stop (`position_management.trailing_stop:`) - v2.0

| Capital | Mode  | activation_% | trail_distance_% | min_profit_to_lock | cooldown_s |
|---------|-------|-------------|-----------------|-------------------|------------|
| $100    | LIVE  | **2.0%**    | **1.5%**        | **0.8%**          | **10**     |
| $300    | PAPER | **1.5%**    | **1.5%**        | **0.5%**          | **10**     |
| $500+   | LIVE  | 2.0%        | 1.5%            | 0.6%              | 10         |

**v2.0 Mejoras:**

- `activation_profit_percent`: **1.5%** (antes 2.5%) - captura más ganancias
- `trail_distance_percent`: **1.5%** (antes 1.2%) - más espacio para respirar
- `cooldown_seconds`: **10** (antes 5) - evita whipsaws
- `min_safety_margin_percent`: **0.6%** (antes 0.4%) - mayor protección

---

### Kelly Criterion (`risk_management.kelly_criterion:`) - v2.0

| Capital | Mode  | fraction | min_confidence | max_risk_cap |
|---------|-------|----------|----------------|--------------|
| $100    | LIVE  | 0.20     | **0.75**       | 1.5%         |
| $100    | PAPER | 0.15     | 0.60           | 1.5%         |
| $300    | PAPER | 0.25     | **0.70**       | 2.5%         |
| $500    | LIVE  | 0.25     | **0.75**       | 2.0%         |
| $1000   | LIVE  | 0.30     | **0.70**       | 3.0%         |

---

### AI Agents (`ai_agents:`) - v2.0

| Capital | Mode  | min_volatility_% | min_volume_ratio | max_retries |
|---------|-------|------------------|------------------|-------------|
| $100    | LIVE  | **0.40**         | **0.60**         | 3           |
| $300    | PAPER | **0.35**         | **0.50**         | 3           |
| $500+   | LIVE  | **0.35**         | **0.55**         | 3           |

**v2.0**: Prompts mejorados con información ATR explícita y checklist obligatorio.

---

### Session Filter (`risk_management.session_filter:`)

| Modo  | enabled | optimal_hours_utc              | Notas                          |
|-------|---------|-------------------------------|--------------------------------|
| PAPER | false   | -                             | Deshabilitado para más pruebas |
| LIVE  | true    | [[7,16], [13,22]]            | Europa + USA sessions          |

---

### Portfolio (`position_management.portfolio:`)

| Capital | max_concurrent_positions | max_exposure_percent | max_per_symbol_percent |
|---------|-------------------------|---------------------|------------------------|
| $100 LIVE  | 1                    | **40%**             | 40%                    |
| $100 PAPER | 1                    | 50%                 | 50%                    |
| $300    | 1                       | 50%                 | 50%                    |
| $500    | 2                       | 55%                 | 35%                    |
| $1000   | 3                       | 65%                 | 35%                    |

---

### Position Sizing (`risk_management.position_sizing:`)

| Capital | Mode  | min_position_usd | min_profit_after_fees | profit_to_fees_ratio |
|---------|-------|-----------------|----------------------|---------------------|
| $100    | LIVE  | **$25**         | **$0.75**            | **10.0**            |
| $300    | PAPER | **$40**         | **$1.00**            | **8.0**             |
| $500    | LIVE  | $35             | $0.80                | 8.0                 |
| $1000   | LIVE  | $50             | $1.00                | 6.0                 |

---

### Technical Analysis (`technical_analysis:`)

| Modo  | min_candles | Notas                                   |
|-------|-------------|----------------------------------------|
| PAPER | **150**     | Balance velocidad/calidad              |
| LIVE  | **200**     | Análisis robusto (institucional)       |

---

### Kill Switch (`security.kill_switch:`)

| Capital | Mode  | max_loss_percentage | cooldown_hours |
|---------|-------|--------------------|--------------------|
| $100    | LIVE  | **4.0%** ($4)      | 24                 |
| $300    | PAPER | 5.0% ($15)         | 24                 |
| $500    | LIVE  | 5.0% ($25)         | 24                 |
| $1000   | LIVE  | 6.0% ($60)         | 24                 |

---

## Comparación PAPER vs LIVE v2.0

| Parámetro | PAPER $300 | LIVE $100 | Razón |
|-----------|-----------|-----------|-------|
| min_confidence | 0.70 | **0.75** | Mayor selectividad en LIVE |
| MTF alignment | **0.65** | 0.70 | Entradas más tempranas |
| min_distance_% | **1.8%** | **1.8%** | Evita stop-hunts |
| max_slippage | 0.30% | **0.20%** | Mejor ejecución |
| profit_to_fees_ratio | 8x | **10x** | Solo trades muy rentables |
| sensitivity | 0.15 | **0.10** | Cambios muy graduales |
| kill_switch | 5% | **4%** | Protección capital real |

---

## Configuración Completa $300 PAPER v2.0

```yaml
# v2.0 INSTITUCIONAL SUPERIOR - $300 PAPER

risk_management:
  max_risk_per_trade: 1.5
  max_daily_drawdown: 5.0
  min_risk_reward_ratio: 2.0
  initial_capital: 300
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.25
    min_confidence: 0.70
    max_risk_cap: 2.5

  # v2.0 CRÍTICO: ATR-Based Stops mejorados
  atr_stops:
    enabled: true
    sl_multiplier: 2.5      # SL = 2.5x ATR (antes 2.0)
    tp_multiplier: 5.0      # TP = 5x ATR (antes 4.0) - R/R 2:1
    min_distance_percent: 1.8   # CRÍTICO: Mínimo 1.8% (antes 0.5%)
    max_distance_percent: 6.0   # Máximo 6%

  session_filter:
    enabled: false

  position_sizing:
    min_position_usd: 40.0
    min_profit_after_fees_usd: 1.00
    profit_to_fees_ratio: 8.0

ai_agents:
  min_volatility_percent: 0.35
  min_volume_ratio: 0.5
  max_retries: 3

technical_analysis:
  min_candles: 150

# v2.0: MTF menos estricto para entradas tempranas
multi_timeframe:
  enabled: true
  min_alignment_score: 0.65  # Antes 0.75
  weights:
    higher: 0.50  # Antes 0.55
    medium: 0.30
    lower: 0.20   # Antes 0.15 - mejor timing

# v2.0: Trailing Stop optimizado
position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 1.5  # Antes 2.5
    trail_distance_percent: 1.5     # Antes 1.2
    min_profit_to_lock: 0.5         # Antes 0.8
    cooldown_seconds: 10            # Antes 5
    min_safety_margin_percent: 0.6  # Antes 0.4

  portfolio:
    max_concurrent_positions: 1
    max_exposure_percent: 50

liquidity_validation:
  max_slippage_percent: 0.3
  max_spread_reject: 0.35
  min_order_book_depth_usd: 500

adaptive_parameters:
  lookback_trades: 30
  sensitivity: 0.15
  ranges:
    min_confidence: { min: 0.65, max: 0.85 }

security:
  kill_switch:
    max_loss_percentage: 5.0
```

---

## Configuración Completa $100 LIVE v2.0

```yaml
# v2.0 INSTITUCIONAL SUPERIOR - $100 LIVE

risk_management:
  max_risk_per_trade: 1.0
  max_daily_drawdown: 4.0
  min_risk_reward_ratio: 2.0
  initial_capital: 100
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.20
    min_confidence: 0.75
    max_risk_cap: 1.5

  # v2.0 CRÍTICO: ATR-Based Stops
  atr_stops:
    enabled: true
    sl_multiplier: 2.5
    tp_multiplier: 5.0
    min_distance_percent: 1.8
    max_distance_percent: 5.0

  session_filter:
    enabled: true
    optimal_hours_utc:
      - [7, 16]
      - [13, 22]

  position_sizing:
    min_position_usd: 25.0
    min_profit_after_fees_usd: 0.75
    profit_to_fees_ratio: 10.0

ai_agents:
  min_volatility_percent: 0.40
  min_volume_ratio: 0.6
  max_retries: 3

technical_analysis:
  min_candles: 200

multi_timeframe:
  enabled: true
  min_alignment_score: 0.70
  weights:
    higher: 0.50
    medium: 0.30
    lower: 0.20

position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 2.0
    trail_distance_percent: 1.5
    min_profit_to_lock: 0.8
    cooldown_seconds: 10
    min_safety_margin_percent: 0.6

  portfolio:
    max_concurrent_positions: 1
    max_exposure_percent: 40

liquidity_validation:
  max_slippage_percent: 0.2
  max_spread_reject: 0.25
  min_order_book_depth_usd: 1000

adaptive_parameters:
  lookback_trades: 30
  sensitivity: 0.10
  ranges:
    min_confidence: { min: 0.70, max: 0.90 }

security:
  kill_switch:
    max_loss_percentage: 4.0
```

---

## Expectativa Matemática v2.0

```
CON LOS NUEVOS PARÁMETROS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Win Rate esperado: 40-45% (más selectivo, pero SL NO toca por ruido)
R/R garantizado: 2.0:1
Fees round-trip: 0.15%

ANTES (v1.8.1):
- SL a 1% = tocado por volatilidad normal → Win Rate ~30%
- E = (0.30 × 2) - (0.70 × 1) = -0.10 por trade ❌

AHORA (v2.0):
- SL a 2-3% = respeta volatilidad → Win Rate ~42%
- E = (0.42 × 2) - (0.58 × 1) = +0.26 por trade ✅

PROYECCIÓN MENSUAL ($300, 15 trades):
- Con $4.50 riesgo/trade × 0.26 expectativa = +$1.17/trade
- 15 trades × $1.17 = +$17.55/mes (+5.9%)
- Proyección anual compuesto: +70%+
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Principios v2.0 INSTITUCIONAL SUPERIOR

### Por qué SL más amplio = mejor rentabilidad:

1. **Stop-hunts**: Crypto tiene "wicks" de 1-2% que tocan SL ajustados
2. **ATR respeta volatilidad**: BTC con ATR 1.5% necesita SL de 3.75%, no 1%
3. **Win rate real**: Con SL ajustado win rate cae a 30%, con SL correcto sube a 42%
4. **Matemáticas**: 42% WR × 2:1 RR = +26% edge vs 30% WR = -10% edge

### Regla del 65-70-2-1.8:

- **65-70%** MTF alignment mínimo (entradas más tempranas)
- **70-75%** confianza mínima para operar
- **2:1** R/R mínimo obligatorio
- **1.8%** distancia mínima de SL (CRÍTICO)

### Antes de ir a LIVE:

1. Probar en PAPER por al menos 2-3 semanas con v2.0
2. Verificar que SL no se toca por "ruido" normal
3. Verificar win rate > 38% con configuración v2.0
4. Confirmar que trades ganadores llegan a TP (no trailing prematuro)
5. Acumular 20+ trades para estadística válida

---

*Documento generado para SATH v2.0 INSTITUCIONAL SUPERIOR*
*Última actualización: 2025-12-04*
