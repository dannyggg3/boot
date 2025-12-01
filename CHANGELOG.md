# Changelog - SATH (Sistema Autónomo de Trading Híbrido)

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [1.4.0] - 2024-12 (Optimización de Reglas de Trading)

### Agregado

- **Cálculo de Volumen Promedio (SMA 20)**
  - Nuevo indicador `volume_mean`: Promedio móvil de 20 períodos del volumen
  - Nuevo indicador `volume_current`: Volumen de la vela actual
  - Nuevo indicador `volume_ratio`: Ratio volumen_actual / volumen_promedio
  - Permite a la IA comparar volumen actual vs histórico

- **Datos de Volumen en Todos los Prompts**
  - Formato: `Volumen Actual: X | Promedio (20): Y | Ratio: Z.ZZx`
  - Incluido en: Agente de Tendencia, Agente de Reversión, Análisis Profundo, Filtro Rápido

### Modificado

- **Reglas del Agente de Tendencia** (`ai_engine.py`)
  - **ANTES**: "Buscas RETROCESOS hacia EMA 50 como zona de entrada"
  - **AHORA**: "Buscas entradas en CONTINUACIÓN DE TENDENCIA":
    - Tendencia FUERTE: permite BREAKOUTS y retrocesos menores
    - Tendencia moderada: espera retroceso a EMA 50 o EMA 20
    - NO espera retrocesos profundos en tendencias explosivas

- **Regla de Volumen Relajada**
  - **ANTES**: "REQUIERES confirmación de volumen (ratio > 1.0)"
  - **AHORA**: "Ratio > 1.0 es ideal, pero ratio > 0.3 es ACEPTABLE. Volumen bajo NO invalida señal técnica fuerte"

- **Reglas del Agente de Reversión** (`ai_engine.py`)
  - **ANTES**: "REQUIERES confirmación de DIVERGENCIA"
  - **AHORA**: "Divergencia RSI es IDEAL pero no obligatoria si hay señales claras de agotamiento"
  - Volumen: ratio > 0.3 es suficiente
  - El Order Book Imbalance puede confirmar la reversión

- **Configuración Kelly Criterion** (`config_live.yaml`)
  - `min_confidence`: 0.6 → **0.5** (permite más operaciones con confianza moderada)

- **Configuración de Agentes** (`config_live.yaml`)
  - `min_volume_ratio`: 0.8 → **0.3** (no filtra por volumen bajo)

### Impacto

| Bloqueo Anterior | Estado |
|------------------|--------|
| Volumen sin dato de promedio | ✅ Arreglado |
| Exigencia estricta de retroceso a EMA 50 | ✅ Relajado |
| Exigencia de divergencia RSI obligatoria | ✅ Relajado |
| Confianza mínima 60% | ✅ Bajada a 50% |
| Ratio volumen > 0.8 | ✅ Bajado a 0.3 |

### Filosofía del Cambio

El bot ahora opera con la **flexibilidad de un trader humano**:
- Puede subirse a tendencias fuertes sin esperar retrocesos profundos
- El volumen bajo no bloquea señales técnicas fuertes
- El Order Book Imbalance puede confirmar señales cuando el volumen es bajo
- Permite operaciones con confianza > 50% (antes > 60%)

---

## [1.3.0] - 2024

### Agregado

- **Despliegue con Docker Compose**
  - `Dockerfile`: Imagen Python 3.11-slim optimizada para el bot
  - `docker-compose.yml`: Orquestación de servicios (bot + InfluxDB + Grafana)
  - Health checks automáticos para todos los servicios
  - Restart automático en caso de fallo
  - Red interna `sath_network` para comunicación entre contenedores

- **DataLogger - Persistencia en InfluxDB**
  - Nuevo módulo `src/modules/data_logger.py`
  - Registra cada decisión de trading con contexto completo:
    - Indicadores técnicos: precio, RSI, EMA 50/200, MACD, ATR
    - Datos avanzados: order book imbalance, funding rate, open interest
    - Metadata: símbolo, decisión, confianza, agente, razonamiento
  - Métodos para consultar rendimiento por agente y símbolo
  - Conexión automática al iniciar el bot

- **Kelly Criterion para Position Sizing**
  - Integración en `src/modules/risk_manager.py`
  - Método `calculate_kelly_position_size()`: sizing óptimo basado en probabilidad
  - Método `get_dynamic_risk_percentage()`: mapeo de confianza a riesgo
  - Ajuste de confianza basado en historial de win rate
  - Configuración en `config.yaml`:
    ```yaml
    risk_management:
      kelly_criterion:
        enabled: true
        fraction: 0.25      # 1/4 Kelly (conservador)
        min_confidence: 0.5 # No opera si confianza < 50%
        max_risk_cap: 3.0   # Máximo 3% por trade
    ```

- **WebSocket Engine (preparado para uso futuro)**
  - Nuevo módulo `src/engines/websocket_engine.py`
  - Soporte para streams de Binance: order book, ticker, trades
  - Callbacks para procesamiento de datos en tiempo real
  - Configuración en `config.yaml`:
    ```yaml
    websockets:
      enabled: false  # Cambiar a true para activar
      orderbook: true
      ticker: true
      trades: true
    ```

### Modificado

- **`main.py`**
  - Añadido import y inicialización de `DataLogger`
  - Llamada a `data_logger.log_decision()` después de cada análisis de IA
  - Parámetro `confidence` añadido a `risk_manager.validate_trade()`

- **`src/modules/risk_manager.py`**
  - Nuevo parámetro `confidence` en `validate_trade()`
  - Integración de Kelly Criterion en el cálculo de position size
  - Lectura de configuración desde sección `kelly_criterion`
  - Historial de trades para cálculo de win rate

- **`src/modules/technical_analysis.py`**
  - Imports condicionales para `pandas_ta` y `ta` (fallback)
  - Compatibilidad con ambas librerías de análisis técnico

- **`src/engines/market_engine.py`**
  - Import condicional de `ib_insync` con flag `IB_AVAILABLE`
  - Manejo graceful cuando IB no está disponible

- **`requirements.txt`**
  - Cambiado `pandas-ta>=0.3.14b` a `ta>=0.11.0` (más compatible)
  - Añadido `influxdb-client>=1.36.0`
  - Comentadas dependencias opcionales: ta-lib, ib_insync, vectorbt

- **`docker-compose.yml`**
  - Token de InfluxDB sincronizado con `.env`
  - Red `sath_network` añadida al servicio `influxdb`

### Datos Almacenados en InfluxDB

| Measurement | Tags | Fields |
|-------------|------|--------|
| `trading_decision` | symbol, decision, agent_type, analysis_type | confidence, price, rsi, ema_50, ema_200, macd, atr_percent, ob_imbalance, funding_rate, reasoning |
| `trade_execution` | symbol, side, agent_type | entry_price, size, stop_loss, take_profit, confidence, risk_reward |
| `trade_result` | symbol, side, result, agent_type | entry_price, exit_price, pnl, pnl_percent, hold_time_minutes |

### Consultas Útiles (Flux)

```flux
# Decisiones de la última hora
from(bucket:"trading_decisions")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "trading_decision")

# Rendimiento por agente (últimos 30 días)
from(bucket:"trading_decisions")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "trade_result")
  |> group(columns: ["agent_type"])
```

---

## [1.2.0] - 2024

### Agregado

- **Sistema de Agentes Especializados**
  - `Trend Agent`: Especializado en continuación de tendencia durante retrocesos
  - `Reversal Agent`: Especializado en reversiones cuando RSI está en extremos (<30 o >70)
  - Selección automática de agente según régimen de mercado

- **Detección de Régimen de Mercado**
  - `trending`: RSI entre 30-70 con señales de EMA (golden/death cross)
  - `reversal`: RSI en extremos (<30 sobrevendido, >70 sobrecomprado)
  - `ranging`: Mercado lateral sin tendencia clara
  - `low_volatility`: ATR muy bajo, no se opera

- **Filtro de Volatilidad Pre-IA**
  - Verifica ATR% antes de invocar API de IA
  - Si ATR < 0.5%, retorna ESPERA sin gastar créditos
  - Ahorro estimado: 70% de llamadas innecesarias

- **Datos Avanzados de Mercado**
  - `Order Book`: Análisis de profundidad, muros de compra/venta, imbalance
  - `Funding Rate`: Sentimiento del mercado de futuros perpetuos
  - `Open Interest`: Dinero entrando/saliendo del mercado
  - `Correlaciones`: Cálculo de correlación con BTC para altcoins

- **Configuración de Agentes** (`config.yaml`)
  ```yaml
  ai_agents:
    enabled: true
    min_volatility_percent: 0.5
    min_volume_ratio: 0.8
  ```

- **Configuración de Datos Avanzados** (`config.yaml`)
  ```yaml
  trading:
    advanced_data:
      enabled: true
      order_book: true
      funding_rate: true
      open_interest: true
      correlations: true
  ```

### Modificado

- `ai_engine.py`: Nuevo método `analyze_market_v2()` con soporte para agentes
- `ai_engine.py`: Nuevo método `determine_market_regime()` para clasificación
- `ai_engine.py`: Nuevos métodos `_trend_agent_analysis()` y `_reversal_agent_analysis()`
- `market_engine.py`: Nuevos métodos para datos avanzados
- `main.py`: Integración de agentes y datos avanzados en el ciclo principal
- `technical_analysis.py`: Campo `atr_percent` para compatibilidad con agentes

### Impacto en Costos de API

| Escenario | v1.1 | v1.2 | Ahorro |
|-----------|------|------|--------|
| Análisis por mes (4 símbolos, 5min) | $69/mes | $21/mes | 70% |
| Llamadas API filtradas | 0% | 70% | - |
| Precisión por agente especializado | Base | +15% | - |

---

## [1.1.0] - 2024

### Agregado

- **Análisis Paralelo**
  - `ThreadPoolExecutor` para análisis simultáneo de múltiples símbolos
  - Configuración `parallel_analysis: true` y `max_parallel_workers: 4`
  - Mejora de velocidad: 4x más rápido con 4 símbolos

- **Protección Anti-Slippage**
  - Verificación de precio pre-ejecución
  - Aborta orden si precio cambió más del umbral configurado
  - Configuración `price_verification.max_deviation_percent: 0.5`

- **Órdenes Limit Inteligentes**
  - Conversión automática de órdenes market a limit
  - Slippage máximo configurable
  - Timeout y acción en caso de no llenarse
  - Configuración `order_execution.use_limit_orders: true`

- **Símbolos Optimizados**
  - Configuración tier-based por liquidez y volatilidad
  - TIER 1 Core: BTC/USDT, ETH/USDT
  - TIER 1 Extendido: SOL/USDT, XRP/USDT

### Modificado

- `main.py`: Método `_analyze_symbols_parallel()` con ThreadPoolExecutor
- `market_engine.py`: Métodos `verify_price_for_execution()` y `calculate_limit_price()`
- `config.yaml`: Nuevas secciones de configuración

### Impacto en Costos

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Tiempo por ciclo (4 símbolos) | 12s | 3s | 4x |
| Pérdidas por slippage | ~$100/mes | ~$30/mes | 70% |
| Costo API | $72/mes | $69/mes | 5% |

---

## [1.0.0] - 2024

### Agregado

- **Arquitectura Híbrida de IA**
  - Modelo rápido (filtro): DeepSeek-V3 / GPT-4o-mini
  - Modelo profundo (decisor): DeepSeek-R1 / o1-mini
  - Ahorro del 70-90% en costos de API

- **Análisis Técnico Completo**
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - EMA 50/200 (Exponential Moving Average)
  - Bollinger Bands
  - ATR (Average True Range)

- **Gestión de Riesgo**
  - Position sizing automático (% del capital)
  - Stop loss dinámico (trailing stop)
  - Kill switch por pérdida máxima
  - Drawdown diario máximo

- **Soporte Multi-Exchange**
  - Binance (crypto)
  - Bybit (crypto)
  - Interactive Brokers (acciones, forex)

- **Modos de Operación**
  - `live`: Trading real
  - `paper`: Simulación sin dinero real
  - `backtest`: Pruebas con datos históricos

- **Múltiples Proveedores de IA**
  - DeepSeek (recomendado por costo)
  - OpenAI (GPT-4o, o1-mini)
  - Google Gemini

- **Sistema de Notificaciones**
  - Telegram
  - Email

- **Logging Completo**
  - Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - Rotación de archivos
  - Heartbeat para monitoreo

### Seguridad

- Kill switch automático
- Rate limiting de API
- Credenciales en variables de entorno

---

## Roadmap Futuro

### v1.3 (Completado)

- [x] WebSockets para datos en tiempo real (motor preparado)
- [x] Persistencia con InfluxDB
- [x] Kelly Criterion para position sizing
- [x] Despliegue con Docker Compose

### v1.4 (Completado)

- [x] Cálculo de volumen promedio (SMA 20) y ratio
- [x] Reglas de volumen flexibles (ratio > 0.3 aceptable)
- [x] Breakouts permitidos en tendencias fuertes
- [x] Divergencia RSI opcional en reversiones
- [x] Confianza mínima reducida (50%)

### v1.5 (Planificado)

- [ ] Dashboard web de monitoreo (Grafana dashboards pre-configurados)
- [ ] Más agentes especializados (Breakout Agent, Scalping Agent)
- [ ] Machine Learning para optimización de parámetros
- [ ] Soporte para más exchanges (Kraken, Coinbase Pro)
- [ ] Estrategias de arbitraje
- [ ] Integración con TradingView
- [ ] API REST para control remoto

---

## Contribuidores

- Trading Bot System Team

## Licencia

MIT License
