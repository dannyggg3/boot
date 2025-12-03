# Guía de Configuración por Nivel de Capital

## Resumen Ejecutivo

Esta guía proporciona configuraciones óptimas para el bot de trading según el capital disponible. A menor capital, más conservador debe ser el enfoque para preservar el capital y permitir recuperación de pérdidas.

**Versión: v1.8.1 INSTITUCIONAL PRO ★★★★★**

---

## Filosofía v1.8.1

```
MENOS TRADES + MAYOR CALIDAD = MEJOR RENTABILIDAD
```

- Solo trades de alta convicción (>70% confianza)
- R/R mínimo 2:1 obligatorio
- ATR-based stops (respeta volatilidad)
- Multi-timeframe alignment requerido

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

> **v1.8.1 CRÍTICO**: `min_risk_reward_ratio` es **SIEMPRE 2.0** - trades con R/R < 2.0 son **RECHAZADOS**

---

### ATR-Based Stops (`risk_management.atr_stops:`) - v1.8+

| Capital | enabled | sl_multiplier | tp_multiplier | min_distance_% | max_distance_% |
|---------|---------|---------------|---------------|----------------|----------------|
| $100 LIVE | true  | 2.0           | 4.0           | 0.5%           | 4.5%           |
| $100 PAPER| true  | 2.0           | 4.0           | 0.5%           | 6.0%           |
| $300 PAPER| true  | 2.0           | 4.0           | 0.5%           | 5.5%           |
| $500+     | true  | 2.0           | 4.0           | 0.5%           | 5.0%           |

**Notas v1.8.1:**

- `sl_multiplier`: SL = Entry ± (ATR × 2.0) - respeta volatilidad del activo
- `tp_multiplier`: TP = Entry ± (ATR × 4.0) - garantiza R/R 2:1
- `min_distance_percent`: SL mínimo 0.5% aunque ATR sea menor
- `max_distance_percent`: LIVE más conservador que PAPER

**Ejemplo BTC con ATR 1.5%:**

- SL = 1.5% × 2 = 3.0%
- TP = 1.5% × 4 = 6.0%
- R/R = 6.0/3.0 = 2:1 ✅

---

### Session Filter (`risk_management.session_filter:`) - v1.8+

| Modo  | enabled | optimal_hours_utc              | Notas                          |
|-------|---------|-------------------------------|--------------------------------|
| PAPER | false   | -                             | Deshabilitado para más pruebas |
| LIVE  | true    | [[7,16], [13,22]]            | Europa + USA sessions          |

**Horarios óptimos:**

- **Europa**: 7:00-16:00 UTC (mayor liquidez EU)
- **USA**: 13:00-22:00 UTC (mayor liquidez US)
- **Fin de semana**: Menor liquidez, más spread

---

### Kelly Criterion (`risk_management.kelly_criterion:`) - v1.8.1

| Capital | Mode  | fraction | min_confidence | max_risk_cap |
|---------|-------|----------|----------------|--------------|
| $100    | LIVE  | 0.20     | **0.75**       | 1.5%         |
| $100    | PAPER | 0.15     | 0.60           | 1.5%         |
| $300    | PAPER | 0.25     | **0.70**       | 2.5%         |
| $500    | LIVE  | 0.25     | **0.75**       | 2.0%         |
| $1000   | LIVE  | 0.30     | **0.70**       | 3.0%         |

**Notas v1.8.1:**

- `fraction`: Porción de Kelly a usar (0.20 = 1/5 Kelly)
- `min_confidence`: **AUMENTADO** - Solo trades de alta convicción
- `max_risk_cap`: Tope máximo de riesgo
- Kelly carga historial real y ajusta según rachas

---

### Technical Analysis (`technical_analysis:`) - v1.8.1

| Modo  | min_candles | Notas                                   |
|-------|-------------|----------------------------------------|
| PAPER | **150**     | Balance velocidad/calidad              |
| LIVE  | **200**     | Análisis robusto (institucional)       |

---

### Multi-Timeframe (`multi_timeframe:`) - v1.8.1

| Modo  | min_alignment_score | higher_weight | medium_weight | lower_weight |
|-------|---------------------|---------------|---------------|--------------|
| PAPER | **0.75** (75%)      | 0.55          | 0.30          | 0.15         |
| LIVE  | **0.80** (80%)      | 0.55          | 0.30          | 0.15         |

**Timeframes:**

- `higher_timeframe`: 4H (tendencia macro - DOMINANTE)
- `medium_timeframe`: 1H (confirmación)
- `lower_timeframe`: 15m (timing de entrada)

---

### AI Agents (`ai_agents:`) - v1.8.1

| Capital | Mode  | min_volatility_% | min_volume_ratio | max_retries |
|---------|-------|------------------|------------------|-------------|
| $100    | LIVE  | **0.40**         | **0.60**         | 3           |
| $300    | PAPER | **0.35**         | **0.50**         | 3           |
| $500+   | LIVE  | **0.35**         | **0.55**         | 3           |

**Notas v1.8.1:**

- Volatilidad y volumen mínimo AUMENTADOS
- Solo opera cuando hay oportunidad real
- Reintentos de API para errores de conexión

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

### Position Sizing (`risk_management.position_sizing:`) - v1.8.1

| Capital | Mode  | min_position_usd | min_profit_after_fees | profit_to_fees_ratio |
|---------|-------|-----------------|----------------------|---------------------|
| $100    | LIVE  | **$25**         | **$0.75**            | **10.0**            |
| $300    | PAPER | **$40**         | **$1.00**            | **8.0**             |
| $500    | LIVE  | $35             | $0.80                | 8.0                 |
| $1000   | LIVE  | $50             | $1.00                | 6.0                 |

**v1.8.1**: Ratios MÁS EXIGENTES para solo trades rentables

---

### Trailing Stop (`position_management.trailing_stop:`) - v1.8.1

| Capital | Mode  | activation_% | trail_distance_% | min_profit_to_lock | cooldown_s |
|---------|-------|-------------|-----------------|-------------------|------------|
| $100    | LIVE  | **3.0%**    | **1.0%**        | **1.0%**          | **5**      |
| $300    | PAPER | **2.5%**    | **1.2%**        | **0.8%**          | **5**      |
| $500+   | LIVE  | 2.5%        | 1.2%            | 0.8%              | 5          |

**v1.8.1 Mejoras:**

- Activación más conservadora
- Trail distance más ajustado (captura más)
- min_profit_to_lock aumentado
- Cooldown aumentado (evita whipsaws)

---

### Liquidity Validation (`liquidity_validation:`) - v1.8.1

| Mode  | max_slippage_% | min_spread_warning | max_spread_reject | min_order_book_usd |
|-------|---------------|-------------------|------------------|-------------------|
| PAPER | **0.30%**     | 0.15%             | **0.35%**        | **$500**          |
| LIVE  | **0.20%**     | **0.10%**         | **0.25%**        | **$1000**         |

**v1.8.1**: Validación MÁS ESTRICTA en LIVE

---

### Adaptive Parameters (`adaptive_parameters:`) - v1.8.1

| Mode  | lookback_trades | sensitivity | min_confidence_range | max_risk_range |
|-------|-----------------|-------------|---------------------|----------------|
| PAPER | **30**          | **0.15**    | 0.65 - 0.85         | 1.0% - 2.5%    |
| LIVE  | **30**          | **0.10**    | 0.70 - 0.90         | 0.5% - 1.5%    |

**v1.8.1**: Más trades para estadística, cambios MÁS GRADUALES

---

### Kill Switch (`security.kill_switch:`)

| Capital | Mode  | max_loss_percentage | cooldown_hours |
|---------|-------|--------------------|--------------------|
| $100    | LIVE  | **4.0%** ($4)      | 24                 |
| $300    | PAPER | 5.0% ($15)         | 24                 |
| $500    | LIVE  | 5.0% ($25)         | 24                 |
| $1000   | LIVE  | 6.0% ($60)         | 24                 |

**v1.8.1**: LIVE más estricto que PAPER

---

## Comparación PAPER vs LIVE v1.8.1

| Parámetro | PAPER $300 | LIVE $100 | Razón |
|-----------|-----------|-----------|-------|
| min_confidence | 0.70 | **0.75** | Mayor selectividad en LIVE |
| MTF alignment | 0.75 | **0.80** | Menos señales falsas |
| min_volatility | 0.35% | **0.40%** | Solo cuando hay movimiento |
| max_slippage | 0.30% | **0.20%** | Mejor ejecución |
| max_spread_reject | 0.35% | **0.25%** | Evita malos spreads |
| profit_to_fees_ratio | 8x | **10x** | Solo trades muy rentables |
| sensitivity | 0.15 | **0.10** | Cambios muy graduales |
| kill_switch | 5% | **4%** | Protección capital real |

---

## Configuración Completa $300 PAPER v1.8.1

```yaml
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

  atr_stops:
    enabled: true
    sl_multiplier: 2.0
    tp_multiplier: 4.0
    min_distance_percent: 0.5
    max_distance_percent: 5.5

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

multi_timeframe:
  enabled: true
  min_alignment_score: 0.75
  weights:
    higher: 0.55
    medium: 0.30
    lower: 0.15

position_management:
  trailing_stop:
    activation_profit_percent: 2.5
    trail_distance_percent: 1.2
    min_profit_to_lock: 0.8
    cooldown_seconds: 5

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

## Configuración Completa $100 LIVE v1.8.1

```yaml
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

  atr_stops:
    enabled: true
    sl_multiplier: 2.0
    tp_multiplier: 4.0
    min_distance_percent: 0.5
    max_distance_percent: 4.5

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
  min_alignment_score: 0.80
  weights:
    higher: 0.55
    medium: 0.30
    lower: 0.15

position_management:
  trailing_stop:
    activation_profit_percent: 3.0
    trail_distance_percent: 1.0
    min_profit_to_lock: 1.0
    cooldown_seconds: 5

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

## Cambios v1.8.1 vs v1.8

| Feature | v1.8 | v1.8.1 | Impacto |
|---------|------|--------|---------|
| min_confidence | 60% | **70-75%** | Mejor win rate |
| Kelly fraction | 0.20 | **0.25** | Mejor sizing |
| MTF alignment | 70% | **75-80%** | Menos falsas |
| min_volatility | 0.25% | **0.35-0.40%** | Mejor R/R |
| min_candles | 100 | **150** | Análisis robusto |
| profit_to_fees | 5x | **8-10x** | Solo rentables |
| trailing activation | 2.0% | **2.5-3.0%** | Más conservador |
| cooldown_seconds | 3 | **5** | Evita whipsaws |

---

## Principios v1.8.1 INSTITUCIONAL PRO

### Por qué menos trades = mejor rentabilidad:

1. **Fees acumulados**: 10 trades × $0.15 = $1.50 vs 3 trades × $0.15 = $0.45
2. **Calidad > Cantidad**: Win rate 60% en 3 trades > Win rate 40% en 10 trades
3. **Capital preservation**: Menos exposición = menos drawdown

### Regla del 70-80-2:

- **70-80%** confianza mínima para operar
- **80%** MTF alignment mínimo (LIVE)
- **2:1** R/R mínimo obligatorio

### Antes de ir a LIVE:

1. Probar en PAPER por al menos 2-3 semanas
2. Verificar win rate > 45% con configuración v1.8.1
3. Confirmar drawdown real < 80% del configurado
4. Acumular 30+ trades para Kelly efectivo
5. Verificar profit factor > 1.5

---

*Documento generado para SATH v1.8.1 INSTITUCIONAL PRO*
*Última actualización: 2025-12-03*
