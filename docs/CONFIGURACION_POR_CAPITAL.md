# Guia de Configuracion por Nivel de Capital

## Resumen Ejecutivo

Esta guia proporciona configuraciones optimas para el bot de trading segun el capital disponible. A menor capital, mas conservador debe ser el enfoque para preservar el capital y permitir recuperacion de perdidas.

**Version: v2.2.2 PROFESIONAL - Calibrado con Trade Ganador Real**

---

## Filosofia v2.2.2

```
CALIDAD > CANTIDAD - Solo operar setups de alta probabilidad
```

### Lecciones del Trade Ganador (+$45.85, +26.2%):

| Parametro | Valor del Trade | Threshold v2.2.2 | Resultado |
|-----------|-----------------|------------------|-----------|
| MTF Alignment | **100%** | 60-65% | Muy por encima |
| Confianza | **85.3%** | 60-65% | Muy por encima |
| Regimen | TRENDING | ADX >= 22 | Confirmado |
| Duracion | 57 min | - | Optima |

**Conclusion**: El trade ganador hubiera pasado facilmente los filtros v2.2.2.

---

## Cambios v2.2.2 vs v2.1

| Feature | v2.1 | v2.2.2 | Impacto |
|---------|------|--------|---------|
| **Cooldown post-cierre** | N/A | **15 min** | Evita re-entrada prematura |
| **Persistencia** | JSON | **SQLite** | Kelly funcional |
| **min_volatility** | 0.3% | **0.5%** | Solo mercados activos |
| **min_adx_trend** | 25 | **22** | Mas oportunidades |
| **MTF alignment** | 65% | **60%** | Mas flexible |
| **min_confidence** | 70% | **60%** | Mas trades |
| **Session filter** | Disabled | **Opcional** | Paper: off, Live: on |

---

## Tabla de Configuraciones por Capital v2.2.2

### Risk Management (`risk_management:`)

| Capital | max_risk_per_trade | max_daily_drawdown | min_risk_reward_ratio | kelly_fraction |
|---------|-------------------|--------------------|-----------------------|----------------|
| $500    | 2.0% ($10)        | 6.0% ($30)         | 1.8                   | 0.30           |
| $1000   | 2.5% ($25)        | 8.0% ($80)         | 1.8                   | 0.40           |
| $2000   | 2.5% ($50)        | 8.0% ($160)        | 1.8                   | 0.45           |
| $5000   | 3.0% ($150)       | 10.0% ($500)       | 2.0                   | 0.50           |
| $10000+ | 3.0% ($300)       | 10.0% ($1000)      | 2.0                   | 0.50           |

---

### Cooldown Post-Cierre v2.2.2 (`position_management.symbol_cooldown_minutes:`)

| Capital | Cooldown | Razon |
|---------|----------|-------|
| **TODOS** | **15 min** | Evita re-entrada emocional/prematura |

**CRITICO**: Sin cooldown, el bot re-entro 17 segundos despues del TP. Con cooldown, espera 15 minutos.

---

### ATR-Based Stops (`risk_management.atr_stops:`)

| Capital | sl_multiplier | tp_multiplier | min_distance_% | max_distance_% |
|---------|---------------|---------------|----------------|----------------|
| $500    | 2.0           | 4.0           | 1.2%           | 6.0%           |
| $1000   | 1.8           | 3.6           | 1.0%           | 5.0%           |
| $2000+  | 1.8           | 3.6           | 1.0%           | 4.5%           |

---

### AI Agents v2.2.2 (`ai_agents:`)

| Modo | min_volatility_% | min_volume_ratio | min_adx_trend |
|------|------------------|------------------|---------------|
| PAPER | **0.5%** | **0.9x** | **22** |
| LIVE  | **0.5%** | **1.0x** | **25** |

---

### Multi-Timeframe (`multi_timeframe:`)

| Modo  | min_alignment_score | higher_weight | medium_weight | lower_weight |
|-------|---------------------|---------------|---------------|--------------|
| PAPER | **0.60** (60%)      | 0.40          | 0.35          | 0.25         |
| LIVE  | **0.65** (65%)      | 0.45          | 0.35          | 0.20         |

---

### Adaptive Parameters v2.2.2 (`adaptive_parameters:`)

| Modo  | default_min_confidence | min_range | max_range |
|-------|------------------------|-----------|-----------|
| PAPER | **0.60** | 0.55 | 0.80 |
| LIVE  | **0.65** | 0.60 | 0.85 |

---

### Portfolio (`position_management.portfolio:`)

| Capital | max_concurrent | max_exposure_% | max_per_symbol_% |
|---------|----------------|----------------|------------------|
| $500    | 1              | 55%            | 55%              |
| $1000   | 2              | 65-70%         | 45%              |
| $2000   | 2              | 70%            | 40%              |
| $5000+  | 3              | 75%            | 35%              |

---

## Configuracion Completa $1000 PAPER v2.2.2 (ACTUAL)

```yaml
# v2.2.2 PROFESIONAL - $1000 PAPER (config_paper.yaml)

risk_management:
  max_risk_per_trade: 3.0         # $30 por operacion
  max_daily_drawdown: 10.0        # $100 maximo
  min_risk_reward_ratio: 1.8
  initial_capital: 1000
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.50
    min_confidence: 0.60
    max_risk_cap: 4.0

  atr_stops:
    enabled: true
    sl_multiplier: 1.8
    tp_multiplier: 3.6
    min_distance_percent: 1.0
    max_distance_percent: 6.0

  session_filter:
    enabled: false                # Deshabilitado en paper

ai_agents:
  enabled: true
  min_volatility_percent: 0.5
  min_volume_ratio: 0.9
  min_adx_trend: 22

multi_timeframe:
  enabled: true
  min_alignment_score: 0.60

adaptive_parameters:
  enabled: true
  default_min_confidence: 0.60
  ranges:
    min_confidence: { min: 0.55, max: 0.80 }

position_management:
  symbol_cooldown_minutes: 15     # CRITICO v2.2.2
  trailing_stop:
    enabled: true
    activation_profit_percent: 1.5
    trail_distance_percent: 0.8
    min_profit_to_lock: 0.5

  portfolio:
    max_concurrent_positions: 2
    max_exposure_percent: 70
```

---

## Configuracion Completa $1000 LIVE v2.2.2

```yaml
# v2.2.2 PROFESIONAL - $1000 LIVE (config_live.yaml)

risk_management:
  max_risk_per_trade: 2.5         # $25 por operacion (mas conservador)
  max_daily_drawdown: 8.0         # $80 maximo
  min_risk_reward_ratio: 1.8
  initial_capital: 1000
  leverage: 1

  kelly_criterion:
    enabled: true
    fraction: 0.40                # Mas conservador en LIVE
    min_confidence: 0.65          # Mas estricto
    max_risk_cap: 3.5

  atr_stops:
    enabled: true
    sl_multiplier: 1.8
    tp_multiplier: 3.6
    min_distance_percent: 1.0
    max_distance_percent: 5.0

  session_filter:
    enabled: true                 # HABILITADO en LIVE
    optimal_hours_utc:
      - [7, 16]
      - [13, 22]

ai_agents:
  enabled: true
  min_volatility_percent: 0.5
  min_volume_ratio: 1.0           # Mas estricto
  min_adx_trend: 25               # Mas estricto

multi_timeframe:
  enabled: true
  min_alignment_score: 0.65       # Mas estricto

adaptive_parameters:
  enabled: true
  default_min_confidence: 0.65
  ranges:
    min_confidence: { min: 0.60, max: 0.85 }

position_management:
  symbol_cooldown_minutes: 15
  trailing_stop:
    enabled: true
    activation_profit_percent: 1.8
    trail_distance_percent: 0.8
    min_profit_to_lock: 0.6

  portfolio:
    max_concurrent_positions: 2
    max_exposure_percent: 65
```

---

## Comparativa PAPER vs LIVE v2.2.2

| Parametro | PAPER | LIVE | Diferencia |
|-----------|-------|------|------------|
| max_risk_per_trade | 3.0% | 2.5% | LIVE -0.5% |
| max_daily_drawdown | 10% | 8% | LIVE -2% |
| kelly_fraction | 0.50 | 0.40 | LIVE -0.10 |
| min_confidence | 0.60 | 0.65 | LIVE +0.05 |
| min_volume_ratio | 0.9x | 1.0x | LIVE +0.1x |
| min_adx_trend | 22 | 25 | LIVE +3 |
| MTF alignment | 60% | 65% | LIVE +5% |
| session_filter | OFF | ON | LIVE habilitado |
| max_exposure | 70% | 65% | LIVE -5% |

**Filosofia**: LIVE es ~15% mas conservador que PAPER en todos los parametros.

---

## Expectativa Matematica v2.2.2

```
BASADO EN TRADE GANADOR REAL:
========================================

Trade: ETH/USDT SHORT
Entry: $3,029.88 → Exit: $2,236.11 (TP)
P&L: +$45.85 (+26.2%)
Confianza: 85.3%
MTF: 100%
Duracion: 57 min

CON v2.2.2 Y $1000:
- Win rate esperado: 45-50%
- R/R promedio: 2:1
- Expectativa: (0.47 × 2) - (0.53 × 1) = +0.41 por trade

PROYECCION MENSUAL:
- 15-20 trades/mes (con cooldown)
- Ganancia promedio por trade: $25 × 0.41 = $10.25
- Mensual: 17 trades × $10.25 = +$174/mes (+17.4%)

PROYECCION ANUAL (compuesto):
- Mes 1: $1,000 → $1,174
- Mes 6: $1,000 → $2,640
- Mes 12: $1,000 → $6,980

**SIN APALANCAMIENTO, SOLO SPOT**
========================================
```

---

## Checklist Antes de LIVE v2.2.2

1. [ ] **Persistencia funcionando**: `risk_manager.db` registra trades
2. [ ] **Cooldown activo**: `symbol_cooldown_minutes: 15`
3. [ ] **Adaptive Parameters**: Singleton inicializado correctamente
4. [ ] **25+ trades en PAPER**: Estadistica valida
5. [ ] **Win rate > 40%**: Expectativa positiva confirmada
6. [ ] **Session filter**: Habilitado en LIVE
7. [ ] **Capital minimo**: $500 recomendado, $1000 optimo

---

## Diagrama de Flujo v2.2.2

```
                    ┌─────────────────┐
                    │  Market Data    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Pre-Filtros    │
                    │  - ADX >= 22    │
                    │  - Vol >= 0.5%  │
                    │  - Volume >= 0.9x│
                    └────────┬────────┘
                             │ Pasa
                    ┌────────▼────────┐
                    │ Cooldown Check  │◄── v2.2.2 NUEVO
                    │ 15 min por symbol│
                    └────────┬────────┘
                             │ OK
                    ┌────────▼────────┐
                    │ MTF Analysis    │
                    │ >= 60% aligned  │
                    └────────┬────────┘
                             │ Pasa
                    ┌────────▼────────┐
                    │ AI Agent        │
                    │ Confianza >= 60%│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Risk Manager    │
                    │ ATR-based SL/TP │
                    │ Kelly sizing    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Execute Trade   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Position Engine │
                    │ - OCO orders    │
                    │ - Trailing Stop │
                    │ - SQLite persist│◄── v2.2.2 FIX
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ On Close:       │
                    │ - Record SQLite │◄── v2.2.2 FIX
                    │ - Set Cooldown  │◄── v2.2.2 NUEVO
                    │ - Notify        │
                    └─────────────────┘
```

---

## Errores Comunes y Soluciones

| Error | Causa | Solucion |
|-------|-------|----------|
| trades no se registran en Kelly | JSON legacy | v2.2.2 usa SQLite |
| re-entrada inmediata | sin cooldown | `symbol_cooldown_minutes: 15` |
| adaptive_state vacio | singleton no inicializado | `get_adaptive_manager(config)` |
| muchos rechazos | filtros muy estrictos | Bajar ADX a 22, MTF a 60% |
| pocos trades | volatilidad baja | Esperar mercado activo |

---

*Documento generado para SATH v2.2.2 PROFESIONAL*
*Ultima actualizacion: 2025-12-06*
*Basado en trade ganador real: +$45.85 (+26.2%)*
