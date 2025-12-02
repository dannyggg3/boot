# Guía de Configuración por Nivel de Capital

## Resumen Ejecutivo

Esta guía proporciona configuraciones óptimas para el bot de trading según el capital disponible. A menor capital, más conservador debe ser el enfoque para preservar el capital y permitir recuperación de pérdidas.

---

## Tabla de Configuraciones Recomendadas

### Risk Management (`risk_management:`)

| Capital | max_risk_per_trade | max_daily_drawdown | min_risk_reward_ratio | leverage |
|---------|-------------------|--------------------|-----------------------|----------|
| $100    | 1.0% ($1)         | 5.0% ($5)          | 1.5                   | 1        |
| $200    | 1.5% ($3)         | 5.0% ($10)         | 1.5                   | 1        |
| $300    | 1.5% ($4.50)      | 6.0% ($18)         | 1.5                   | 1        |
| $400    | 2.0% ($8)         | 6.0% ($24)         | 2.0                   | 1        |
| $500    | 2.0% ($10)        | 7.0% ($35)         | 2.0                   | 1        |
| $600    | 2.0% ($12)        | 7.0% ($42)         | 2.0                   | 1        |
| $700    | 2.0% ($14)        | 8.0% ($56)         | 2.0                   | 1        |
| $800    | 2.5% ($20)        | 8.0% ($64)         | 2.0                   | 1        |
| $900    | 2.5% ($22.50)     | 8.0% ($72)         | 2.0                   | 1        |
| $1000   | 3.0% ($30)        | 10.0% ($100)       | 2.0                   | 1        |

---

### Kelly Criterion (`risk_management.kelly_criterion:`)

| Capital | fraction | min_confidence | max_risk_cap |
|---------|----------|----------------|--------------|
| $100    | 0.15     | 0.65           | 1.5%         |
| $200    | 0.20     | 0.65           | 2.0%         |
| $300    | 0.20     | 0.60           | 2.5%         |
| $400    | 0.25     | 0.60           | 3.0%         |
| $500    | 0.25     | 0.60           | 3.0%         |
| $600    | 0.25     | 0.55           | 3.0%         |
| $700    | 0.30     | 0.55           | 3.5%         |
| $800    | 0.30     | 0.55           | 3.5%         |
| $900    | 0.30     | 0.50           | 4.0%         |
| $1000   | 0.35     | 0.50           | 4.0%         |

**Notas:**
- `fraction`: Porción de Kelly a usar (0.25 = 1/4 Kelly, conservador)
- `min_confidence`: Confianza mínima de la IA para ejecutar trade
- `max_risk_cap`: Tope máximo de riesgo incluso con alta confianza

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
| $100    | 15              | 0.30                     | 4.0                 |
| $200    | 20              | 0.40                     | 4.0                 |
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

| Capital | activation_profit_percent | trail_distance_percent |
|---------|--------------------------|----------------------|
| $100    | 1.5%                     | 1.0%                 |
| $200    | 1.5%                     | 1.0%                 |
| $300    | 1.5%                     | 1.2%                 |
| $400    | 2.0%                     | 1.2%                 |
| $500    | 2.0%                     | 1.5%                 |
| $600    | 2.0%                     | 1.5%                 |
| $700    | 2.0%                     | 1.5%                 |
| $800    | 2.5%                     | 1.5%                 |
| $900    | 2.5%                     | 2.0%                 |
| $1000   | 2.5%                     | 2.0%                 |

**Notas:**
- `activation_profit_percent`: Ganancia mínima para activar trailing stop
- `trail_distance_percent`: Distancia del trailing stop al precio actual
- Con menos capital, activar antes para asegurar ganancias pequeñas

---

### Kill Switch (`security.kill_switch:`)

| Capital | max_loss_percentage | Pérdida Absoluta | cooldown_period_hours |
|---------|--------------------|-----------------|-----------------------|
| $100    | 5.0%               | $5              | 24                    |
| $200    | 5.0%               | $10             | 24                    |
| $300    | 6.0%               | $18             | 24                    |
| $400    | 6.0%               | $24             | 24                    |
| $500    | 7.0%               | $35             | 24                    |
| $600    | 7.0%               | $42             | 24                    |
| $700    | 8.0%               | $56             | 24                    |
| $800    | 8.0%               | $64             | 24                    |
| $900    | 9.0%               | $81             | 24                    |
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

### $100 - Ultra Conservador

```yaml
risk_management:
  max_risk_per_trade: 1.0
  max_daily_drawdown: 5.0
  min_risk_reward_ratio: 1.5
  initial_capital: 100
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.15
    min_confidence: 0.65
    max_risk_cap: 1.5

  position_sizing:
    min_position_usd: 15.0
    min_profit_after_fees_usd: 0.30
    profit_to_fees_ratio: 4.0

position_management:
  trailing_stop:
    activation_profit_percent: 1.5
    trail_distance_percent: 1.0

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

### $300 - Conservador

```yaml
risk_management:
  max_risk_per_trade: 1.5
  max_daily_drawdown: 6.0
  min_risk_reward_ratio: 1.5
  initial_capital: 300
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.20
    min_confidence: 0.60
    max_risk_cap: 2.5

  position_sizing:
    min_position_usd: 25.0
    min_profit_after_fees_usd: 0.50
    profit_to_fees_ratio: 5.0

position_management:
  trailing_stop:
    activation_profit_percent: 1.5
    trail_distance_percent: 1.2

  portfolio:
    max_concurrent_positions: 1
    max_exposure_percent: 50
    max_per_symbol_percent: 50

security:
  kill_switch:
    max_loss_percentage: 6.0

ai_agents:
  min_volatility_percent: 0.25
  min_volume_ratio: 0.3
```

---

### $500 - Moderado

```yaml
risk_management:
  max_risk_per_trade: 2.0
  max_daily_drawdown: 7.0
  min_risk_reward_ratio: 2.0
  initial_capital: 500
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.25
    min_confidence: 0.60
    max_risk_cap: 3.0

  position_sizing:
    min_position_usd: 35.0
    min_profit_after_fees_usd: 0.70
    profit_to_fees_ratio: 5.0

position_management:
  trailing_stop:
    activation_profit_percent: 2.0
    trail_distance_percent: 1.5

  portfolio:
    max_concurrent_positions: 2
    max_exposure_percent: 55
    max_per_symbol_percent: 35

security:
  kill_switch:
    max_loss_percentage: 7.0

ai_agents:
  min_volatility_percent: 0.25
  min_volume_ratio: 0.3
```

---

### $750 - Balanceado

```yaml
risk_management:
  max_risk_per_trade: 2.0
  max_daily_drawdown: 8.0
  min_risk_reward_ratio: 2.0
  initial_capital: 750
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.30
    min_confidence: 0.55
    max_risk_cap: 3.5

  position_sizing:
    min_position_usd: 45.0
    min_profit_after_fees_usd: 0.90
    profit_to_fees_ratio: 5.0

position_management:
  trailing_stop:
    activation_profit_percent: 2.0
    trail_distance_percent: 1.5

  portfolio:
    max_concurrent_positions: 2
    max_exposure_percent: 60
    max_per_symbol_percent: 40

security:
  kill_switch:
    max_loss_percentage: 8.0

ai_agents:
  min_volatility_percent: 0.20
  min_volume_ratio: 0.3
```

---

### $1000 - Estándar

```yaml
risk_management:
  max_risk_per_trade: 3.0
  max_daily_drawdown: 10.0
  min_risk_reward_ratio: 2.0
  initial_capital: 1000
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.35
    min_confidence: 0.50
    max_risk_cap: 4.0

  position_sizing:
    min_position_usd: 60.0
    min_profit_after_fees_usd: 1.20
    profit_to_fees_ratio: 5.0

position_management:
  trailing_stop:
    activation_profit_percent: 2.5
    trail_distance_percent: 2.0

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

## Principios Generales

### Por qué ser más conservador con menos capital:

1. **Impacto de fees**: Con $100, las comisiones de $0.15 representan un % mayor
2. **Capacidad de recuperación**: Una pérdida de 10% requiere 11% de ganancia para recuperar
3. **Diversificación limitada**: No puedes distribuir riesgo en múltiples posiciones
4. **Margen de error**: Menos capital = menos oportunidades de corregir errores

### Regla del 1-2-3:

- **$100-300**: Riesgo 1-1.5% por trade, máximo 1 posición
- **$300-600**: Riesgo 1.5-2% por trade, máximo 2 posiciones
- **$600-1000**: Riesgo 2-3% por trade, máximo 3 posiciones

### Antes de ir a LIVE:

1. Probar en PAPER por al menos 2 semanas
2. Verificar que win rate > 45% con la configuración elegida
3. Confirmar que drawdown máximo real < configurado
4. Revisar que profit factor > 1.2 (ganancias/pérdidas)

---

*Documento generado para SATH v1.6*
*Última actualización: 2025-12-02*
