# Guía de Configuración por Nivel de Capital

## Resumen Ejecutivo

Esta guía proporciona configuraciones óptimas para el bot de trading según el capital disponible. A menor capital, más conservador debe ser el enfoque para preservar el capital y permitir recuperación de pérdidas.

**Versión: v1.8 INSTITUCIONAL**

---

## Tabla de Configuraciones Recomendadas

### Risk Management (`risk_management:`)

| Capital | max_risk_per_trade | max_daily_drawdown | min_risk_reward_ratio | leverage |
|---------|-------------------|--------------------|-----------------------|----------|
| $100    | 1.0% ($1)         | 5.0% ($5)          | **2.0**               | 1        |
| $200    | 1.0% ($2)         | 5.0% ($10)         | **2.0**               | 1        |
| $300    | 1.5% ($4.50)      | 5.0% ($15)         | **2.0**               | 1        |
| $400    | 1.5% ($6)         | 6.0% ($24)         | **2.0**               | 1        |
| $500    | 1.5% ($7.50)      | 6.0% ($30)         | **2.0**               | 1        |
| $600    | 2.0% ($12)        | 7.0% ($42)         | **2.0**               | 1        |
| $700    | 2.0% ($14)        | 7.0% ($49)         | **2.0**               | 1        |
| $800    | 2.0% ($16)        | 8.0% ($64)         | **2.0**               | 1        |
| $900    | 2.5% ($22.50)     | 8.0% ($72)         | **2.0**               | 1        |
| $1000   | 2.5% ($25)        | 10.0% ($100)       | **2.0**               | 1        |

> **v1.8 CRÍTICO**: `min_risk_reward_ratio` es **SIEMPRE 2.0** - trades con R/R < 2.0 son **RECHAZADOS**

---

### ATR-Based Stops (`risk_management.atr_stops:`) - v1.8 NUEVO

| Capital | enabled | sl_multiplier | tp_multiplier | min_distance_% | max_distance_% |
|---------|---------|---------------|---------------|----------------|----------------|
| $100    | true    | 2.0           | 4.0           | 0.5%           | 6.0%           |
| $200    | true    | 2.0           | 4.0           | 0.5%           | 6.0%           |
| $300    | true    | 2.0           | 4.0           | 0.5%           | 5.5%           |
| $400    | true    | 2.0           | 4.0           | 0.5%           | 5.5%           |
| $500    | true    | 2.0           | 4.0           | 0.5%           | 5.0%           |
| $600+   | true    | 2.0           | 4.0           | 0.5%           | 5.0%           |

**Notas v1.8:**
- `sl_multiplier`: SL = Entry ± (ATR × 2.0) - respeta volatilidad del activo
- `tp_multiplier`: TP = Entry ± (ATR × 4.0) - garantiza R/R 2:1
- `min_distance_percent`: SL mínimo 0.5% aunque ATR sea menor
- `max_distance_percent`: SL máximo aunque ATR sea mayor (más conservador en LIVE)

**Ejemplo BTC con ATR 1.5%:**
- SL = 1.5% × 2 = 3.0%
- TP = 1.5% × 4 = 6.0%
- R/R = 6.0/3.0 = 2:1 ✅

---

### Session Filter (`risk_management.session_filter:`) - v1.8 NUEVO

| Modo  | enabled | optimal_hours_utc              | Notas                          |
|-------|---------|-------------------------------|--------------------------------|
| PAPER | false   | -                             | Deshabilitado para más pruebas |
| LIVE  | true    | [[7,16], [13,22]]            | Europa + USA sessions          |

**Notas v1.8:**
- **Europa**: 7:00-16:00 UTC (mayor liquidez EU)
- **USA**: 13:00-22:00 UTC (mayor liquidez US)
- Fin de semana (Sáb-Dom) = menor liquidez, más spread
- En LIVE evita operar fuera de horarios óptimos

---

### Kelly Criterion (`risk_management.kelly_criterion:`)

| Capital | fraction | min_confidence | max_risk_cap |
|---------|----------|----------------|--------------|
| $100    | 0.15     | 0.60           | 1.5%         |
| $200    | 0.15     | 0.60           | 1.5%         |
| $300    | 0.20     | 0.60           | 2.0%         |
| $400    | 0.20     | 0.60           | 2.5%         |
| $500    | 0.25     | 0.55           | 2.5%         |
| $600    | 0.25     | 0.55           | 3.0%         |
| $700    | 0.25     | 0.55           | 3.0%         |
| $800    | 0.30     | 0.50           | 3.5%         |
| $900    | 0.30     | 0.50           | 3.5%         |
| $1000   | 0.35     | 0.50           | 4.0%         |

**Notas v1.8:**
- `fraction`: Porción de Kelly a usar (0.15 = 1/6 Kelly, muy conservador)
- `min_confidence`: Confianza mínima de la IA para ejecutar trade
- `max_risk_cap`: Tope máximo de riesgo incluso con alta confianza
- **v1.8**: Kelly ahora carga historial real y ajusta según rachas de pérdidas

---

### Technical Analysis (`technical_analysis:`) - v1.8 NUEVO

| Modo  | min_candles | Notas                                   |
|-------|-------------|----------------------------------------|
| PAPER | 100         | Más flexibilidad para pruebas rápidas  |
| LIVE  | 200         | Análisis más confiable (institucional) |

**Notas v1.8:**
- EMA 200 necesita 200+ velas
- ATR confiable necesita 100+ velas
- En LIVE, siempre usar 200 velas mínimo

---

### Portfolio (`position_management.portfolio:`)

| Capital | max_concurrent_positions | max_exposure_percent | max_per_symbol_percent |
|---------|-------------------------|---------------------|------------------------|
| $100    | 1                       | 40%                 | 40%                    |
| $200    | 1                       | 45%                 | 45%                    |
| $300    | 1                       | 50%                 | 50%                    |
| $400    | 2                       | 50%                 | 35%                    |
| $500    | 2                       | 55%                 | 35%                    |
| $600    | 2                       | 55%                 | 35%                    |
| $700    | 2                       | 60%                 | 40%                    |
| $800    | 3                       | 60%                 | 30%                    |
| $900    | 3                       | 65%                 | 30%                    |
| $1000   | 3                       | 70%                 | 35%                    |

**Notas:**
- Con menos capital, concentrar en 1 posición reduce impacto de fees
- Más capital permite diversificar en múltiples posiciones

---

### Position Sizing (`risk_management.position_sizing:`)

| Capital | min_position_usd | min_profit_after_fees_usd | profit_to_fees_ratio |
|---------|-----------------|--------------------------|---------------------|
| $100    | 15              | 0.50                     | 5.0                 |
| $200    | 20              | 0.50                     | 5.0                 |
| $300    | 25              | 0.50                     | 5.0                 |
| $400    | 30              | 0.60                     | 5.0                 |
| $500    | 35              | 0.70                     | 5.0                 |
| $600    | 40              | 0.80                     | 5.0                 |
| $700    | 45              | 0.90                     | 5.0                 |
| $800    | 50              | 1.00                     | 5.0                 |
| $900    | 55              | 1.10                     | 5.0                 |
| $1000   | 60              | 1.20                     | 5.0                 |

---

### Trailing Stop (`position_management.trailing_stop:`)

| Capital | activation_profit_percent | trail_distance_percent | cooldown_seconds | min_safety_margin_percent |
|---------|--------------------------|----------------------|------------------|---------------------------|
| $100    | 2.0%                     | 1.5%                 | 3                | 0.3%                      |
| $200    | 2.0%                     | 1.5%                 | 3                | 0.3%                      |
| $300    | 2.0%                     | 1.5%                 | 3                | 0.3%                      |
| $400    | 2.0%                     | 1.5%                 | 3                | 0.3%                      |
| $500    | 2.0%                     | 1.5%                 | 3                | 0.3%                      |
| $600    | 2.5%                     | 1.5%                 | 3                | 0.3%                      |
| $700    | 2.5%                     | 2.0%                 | 3                | 0.3%                      |
| $800    | 2.5%                     | 2.0%                 | 3                | 0.3%                      |
| $900    | 2.5%                     | 2.0%                 | 3                | 0.3%                      |
| $1000   | 3.0%                     | 2.0%                 | 3                | 0.3%                      |

**Notas:**
- `activation_profit_percent`: Ganancia mínima para activar trailing stop
- `trail_distance_percent`: Distancia del trailing stop al precio actual
- `cooldown_seconds`: Tiempo mínimo entre actualizaciones de SL (evita race conditions)
- `min_safety_margin_percent`: Margen mínimo entre precio y SL (evita triggers inmediatos)
- **IMPORTANTE**: `trail_distance` debe ser < `activation_profit` para asegurar ganancias

---

### Paper Mode Simulation (`paper_simulation:`)

| Capital | min_latency_ms | max_latency_ms | base_slippage_percent | max_slippage_percent | failure_rate |
|---------|----------------|----------------|----------------------|---------------------|--------------|
| Todos   | 50             | 200            | 0.05                 | 0.15                | 0.02         |

**Notas:**
- Simula condiciones reales de mercado para paper trading
- Ayuda a tener expectativas realistas antes de ir a LIVE
- `failure_rate`: 2% de fallos simulados de red

---

### Validación de Liquidez (`liquidity_validation:`)

| Modo  | enabled | max_slippage_percent | min_spread_warning | max_spread_reject |
|-------|---------|---------------------|-------------------|------------------|
| PAPER | true    | 0.5%                | 0.3%              | 0.5%             |
| LIVE  | true    | 0.3%                | 0.2%              | 0.4%             |

**Notas:**
- Verifica liquidez del order book antes de ejecutar órdenes
- LIVE más estricto que PAPER
- Rechaza operaciones si spread excede máximo

---

### Kill Switch (`security.kill_switch:`)

| Capital | max_loss_percentage | Pérdida Absoluta | cooldown_period_hours |
|---------|--------------------|-----------------|-----------------------|
| $100    | 5.0%               | $5              | 24                    |
| $200    | 5.0%               | $10             | 24                    |
| $300    | 5.0%               | $15             | 24                    |
| $400    | 6.0%               | $24             | 24                    |
| $500    | 6.0%               | $30             | 24                    |
| $600    | 7.0%               | $42             | 24                    |
| $700    | 7.0%               | $49             | 24                    |
| $800    | 8.0%               | $64             | 24                    |
| $900    | 8.0%               | $72             | 24                    |
| $1000   | 10.0%              | $100            | 24                    |

---

### Trading Settings (`trading:`)

| Capital | symbols (cantidad) | timeframe | scan_interval |
|---------|-------------------|-----------|---------------|
| $100    | 2-3               | 15m       | 180s          |
| $200    | 2-3               | 15m       | 180s          |
| $300    | 3                 | 15m       | 180s          |
| $400    | 3                 | 15m       | 180s          |
| $500    | 3-4               | 15m/1h    | 180s          |
| $600    | 3-4               | 15m/1h    | 180s          |
| $700    | 4                 | 1h        | 300s          |
| $800    | 4                 | 1h        | 300s          |
| $900    | 4-5               | 1h        | 300s          |
| $1000   | 4-5               | 1h        | 300s          |

**Símbolos recomendados por prioridad:**
1. BTC/USDT (siempre incluir)
2. ETH/USDT (siempre incluir)
3. SOL/USDT (alta volatilidad)
4. XRP/USDT (buena liquidez)
5. BNB/USDT (opcional)

---

### AI Agents (`ai_agents:`)

| Capital | min_volatility_percent | min_volume_ratio |
|---------|----------------------|------------------|
| $100    | 0.30                 | 0.4              |
| $200    | 0.30                 | 0.4              |
| $300    | 0.25                 | 0.3              |
| $400    | 0.25                 | 0.3              |
| $500    | 0.25                 | 0.3              |
| $600    | 0.20                 | 0.3              |
| $700    | 0.20                 | 0.3              |
| $800    | 0.15                 | 0.2              |
| $900    | 0.15                 | 0.2              |
| $1000   | 0.10                 | 0.2              |

**Notas:**
- Con menos capital, ser más selectivo (mayor min_volatility)
- Esto reduce cantidad de trades pero aumenta calidad

---

## Configuraciones Completas por Capital

### $100 - Ultra Conservador (v1.8)

```yaml
risk_management:
  max_risk_per_trade: 1.0
  max_daily_drawdown: 5.0
  min_risk_reward_ratio: 2.0  # v1.8: SIEMPRE 2.0
  initial_capital: 100
  leverage: 1

  # v1.8: ATR-based Stops
  atr_stops:
    enabled: true
    sl_multiplier: 2.0
    tp_multiplier: 4.0
    min_distance_percent: 0.5
    max_distance_percent: 6.0

  # v1.8: Session Filter
  session_filter:
    enabled: false  # Deshabilitado en paper
    optimal_hours_utc:
      - [7, 16]
      - [13, 22]

  kelly_criterion:
    enabled: true
    fraction: 0.15
    min_confidence: 0.60
    max_risk_cap: 1.5

  position_sizing:
    min_position_usd: 15.0
    min_profit_after_fees_usd: 0.50
    profit_to_fees_ratio: 5.0

# v1.8: Technical Analysis
technical_analysis:
  min_candles: 100  # 200 para LIVE

position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 2.0
    trail_distance_percent: 1.5
    cooldown_seconds: 3
    min_safety_margin_percent: 0.3

  portfolio:
    max_concurrent_positions: 1
    max_exposure_percent: 40
    max_per_symbol_percent: 40

security:
  kill_switch:
    max_loss_percentage: 5.0

ai_agents:
  min_volatility_percent: 0.30
  min_volume_ratio: 0.4
```

---

### $500 - Moderado (v1.8)

```yaml
risk_management:
  max_risk_per_trade: 1.5
  max_daily_drawdown: 6.0
  min_risk_reward_ratio: 2.0
  initial_capital: 500
  leverage: 1

  atr_stops:
    enabled: true
    sl_multiplier: 2.0
    tp_multiplier: 4.0
    min_distance_percent: 0.5
    max_distance_percent: 5.0

  session_filter:
    enabled: true
    optimal_hours_utc:
      - [7, 16]
      - [13, 22]

  kelly_criterion:
    enabled: true
    fraction: 0.25
    min_confidence: 0.55
    max_risk_cap: 2.5

  position_sizing:
    min_position_usd: 35.0
    min_profit_after_fees_usd: 0.70
    profit_to_fees_ratio: 5.0

technical_analysis:
  min_candles: 200

position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 2.0
    trail_distance_percent: 1.5
    cooldown_seconds: 3
    min_safety_margin_percent: 0.3

  portfolio:
    max_concurrent_positions: 2
    max_exposure_percent: 55
    max_per_symbol_percent: 35

security:
  kill_switch:
    max_loss_percentage: 6.0

ai_agents:
  min_volatility_percent: 0.25
  min_volume_ratio: 0.3
```

---

### $1000 - Estándar (v1.8)

```yaml
risk_management:
  max_risk_per_trade: 2.5
  max_daily_drawdown: 10.0
  min_risk_reward_ratio: 2.0
  initial_capital: 1000
  leverage: 1

  atr_stops:
    enabled: true
    sl_multiplier: 2.0
    tp_multiplier: 4.0
    min_distance_percent: 0.5
    max_distance_percent: 5.0

  session_filter:
    enabled: true
    optimal_hours_utc:
      - [7, 16]
      - [13, 22]

  kelly_criterion:
    enabled: true
    fraction: 0.35
    min_confidence: 0.50
    max_risk_cap: 4.0

  position_sizing:
    min_position_usd: 60.0
    min_profit_after_fees_usd: 1.20
    profit_to_fees_ratio: 5.0

technical_analysis:
  min_candles: 200

position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 3.0
    trail_distance_percent: 2.0
    cooldown_seconds: 3
    min_safety_margin_percent: 0.3

  portfolio:
    max_concurrent_positions: 3
    max_exposure_percent: 70
    max_per_symbol_percent: 35

security:
  kill_switch:
    max_loss_percentage: 10.0

ai_agents:
  min_volatility_percent: 0.10
  min_volume_ratio: 0.2
```

---

## Cambios v1.8 INSTITUCIONAL

### Nuevas Características:

| Feature | Descripción | Impacto |
|---------|-------------|---------|
| **ATR-based SL** | Stop Loss dinámico según volatilidad | -50% SL prematuros |
| **ATR-based TP** | Take Profit automático si IA no sugiere | R/R 2:1 garantizado |
| **R/R mínimo 2.0** | Rechaza trades con R/R < 2.0 | Mejor expectativa matemática |
| **Session Filter** | Solo opera en horarios óptimos | Mejor liquidez |
| **Kelly mejorado** | Historial persistente + rachas | Sizing más preciso |
| **Min candles** | 100 paper, 200 live | Análisis más confiable |

### Por qué R/R mínimo 2.0:

Con win rate de 40% (realista):
- R/R 1.5:1 → Expectativa = 0.40×1.5 - 0.60×1 = **0.00** (breakeven)
- R/R 2.0:1 → Expectativa = 0.40×2.0 - 0.60×1 = **+0.20** por trade

---

## Principios Generales

### Por qué ser más conservador con menos capital:

1. **Impacto de fees**: Con $100, las comisiones de $0.15 representan un % mayor
2. **Capacidad de recuperación**: Una pérdida de 10% requiere 11% de ganancia para recuperar
3. **Diversificación limitada**: No puedes distribuir riesgo en múltiples posiciones
4. **Margen de error**: Menos capital = menos oportunidades de corregir errores

### Regla del 1-2-3:

- **$100-300**: Riesgo 1-1.5% por trade, máximo 1 posición
- **$300-600**: Riesgo 1.5-2% por trade, máximo 2 posiciones
- **$600-1000**: Riesgo 2-2.5% por trade, máximo 3 posiciones

### Antes de ir a LIVE:

1. Probar en PAPER por al menos 2 semanas
2. Verificar que win rate > 40% con la configuración elegida
3. Confirmar que drawdown máximo real < configurado
4. Revisar que profit factor > 1.2 (ganancias/pérdidas)
5. **v1.8**: Acumular 20+ trades para que Kelly sea efectivo

---

*Documento generado para SATH v1.8 INSTITUCIONAL*
*Última actualización: 2025-12-03*
