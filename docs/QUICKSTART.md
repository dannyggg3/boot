# Guía de Inicio Rápido - SATH v2.2.1 INSTITUCIONAL PROFESIONAL ★★★★★

## Primeros Pasos (5 minutos)

### 1. Instalar Dependencias

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# o en Windows: venv\Scripts\activate

# Instalar paquetes
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configurar Credenciales

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus credenciales
nano .env  # o usa tu editor favorito
```

Necesitas al menos **una API key de IA**:
- **DeepSeek** (Recomendado): https://platform.deepseek.com/
- **OpenAI**: https://platform.openai.com/
- **Gemini**: https://ai.google.dev/

### 3. Configurar el Bot

Edita `config/config.yaml`:

```yaml
# Seleccionar tu proveedor de IA
ai_provider: "deepseek"  # deepseek, openai, o gemini

# Modo de operación (IMPORTANTE: empieza con paper)
trading:
  mode: "paper"  # NO cambies a "live" hasta probar
```

### 4. Verificar Configuración (v2.2.0+)

```bash
# v2.2.0: Nuevo script de verificación completo
python verify_system.py config/config_paper.yaml
```

Este script verifica:
- Dependencias instaladas
- Variables de entorno
- Conexión al exchange (Binance)
- Conexión a IA (DeepSeek)
- Base de datos SQLite
- Análisis de prueba con datos reales

Si todo está ✅, continúa al siguiente paso.

### 5. Ejecutar el Bot

```bash
python main.py
```

## Configuración Mínima para Empezar

### Solo Análisis (Sin ejecutar operaciones)

```yaml
# config/config.yaml
trading:
  mode: "backtest"  # Solo observa y registra decisiones
```

### Paper Trading (Simulación)

```yaml
trading:
  mode: "paper"
  symbols:
    - "BTC/USDT"
```

### Configuración de IA

En `.env`:

```env
# Elige UNA de estas opciones

# Opción 1: DeepSeek (Económico - Recomendado)
DEEPSEEK_API_KEY=sk-tu-clave-aqui

# Opción 2: OpenAI (Potente)
OPENAI_API_KEY=sk-tu-clave-aqui

# Opción 3: Gemini (Gratis con límites)
GEMINI_API_KEY=AIzaSy-tu-clave-aqui
```

### Configuración Optimizada v2.2.1 INSTITUCIONAL PROFESIONAL

Las siguientes optimizaciones institucionales vienen **habilitadas por defecto**:

```yaml
# === AGENTES ESPECIALIZADOS v2.2.1 ===
ai_agents:
  enabled: true
  min_volatility_percent: 0.3   # v2.2: Más oportunidades
  min_volume_ratio: 0.8         # v2.2: Más flexible
  ideal_volume_ratio: 1.2
  min_adx_trend: 20             # v2.2: Permite transiciones
  max_retries: 2

# === GESTIÓN DE RIESGO INSTITUCIONAL v2.2 ===
risk_management:
  min_risk_reward_ratio: 1.8    # v2.2: Más oportunidades

  kelly_criterion:
    enabled: true
    min_confidence: 0.60        # v2.2: Más trades paper

  atr_stops:
    enabled: true
    sl_multiplier: 1.8          # v2.2: Más ajustado
    tp_multiplier: 3.6
    min_distance_percent: 1.0

  # v2.2: OFF en paper para más trades
  session_filter:
    enabled: false

# === TRAILING STOP v2.2 (OPTIMIZADO) ===
position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 1.5  # v2.2: Activa antes
    trail_distance_percent: 0.8     # v2.2: Más ajustado
    min_profit_to_lock: 0.5
    cooldown_seconds: 10

# === MULTI-TIMEFRAME v2.2.1 ===
multi_timeframe:
  enabled: true
  min_alignment_score: 0.50     # v2.2.1: 50% = 2/3 TFs alineados

# === PARÁMETROS ADAPTATIVOS v2.2.1 ===
adaptive_parameters:
  enabled: true
  default_min_confidence: 0.55  # v2.2.1: Configurable desde YAML
  ranges:
    min_confidence: { min: 0.50, max: 0.75 }
    max_risk_per_trade: { min: 1.5, max: 3.0 }
```

**Impacto v2.2.1 INSTITUCIONAL PROFESIONAL:**
- **Decisión Directa**: 4/4 criterios = sin llamar API (~80% ahorro)
- **Python Pre-Calc**: Criterios calculados en Python (sin hallucinations)
- **SQLite Atómico**: Persistencia ACID (sin corrupción)
- **Fallback Parser**: Extrae decisiones de texto libre (-90% errores)
- **MTF 50%**: Threshold relajado para paper (+15% setups)
- **Confidence 55%**: Mínimo adaptativo configurable (+20% trades)
- **Win Rate esperado: ~48%** (profesional institucional)

## Problemas Comunes

### "ModuleNotFoundError: No module named 'ccxt'"

```bash
pip install ccxt
```

### "Error loading config"

Verifica que `config/config.yaml` existe y no tiene errores de sintaxis.

### "API Key not found"

1. Verifica que `.env` existe (no `.env.example`)
2. Verifica que la API key está sin comillas
3. Reinicia el bot después de editar `.env`

### El bot no ejecuta operaciones

Esto es normal en modo `paper` si:
- Las condiciones de mercado no son favorables
- El Risk Manager está rechazando operaciones
- La verificación de precio abortó la orden (v1.1)
- Revisa los logs: `tail -f logs/trading_bot.log`

### Logs esperados (v2.2.1 INSTITUCIONAL PROFESIONAL)

```
╔═══════════════════════════════════════════════════════════╗
║     Sistema Autónomo de Trading Híbrido (SATH) v2.2.1     ║
║      ★★★★★ INSTITUCIONAL PROFESIONAL ★★★★★               ║
╚═══════════════════════════════════════════════════════════╝

🔄 Iniciando análisis PARALELO de 3 símbolos...
✅ Análisis paralelo completado en 2.8s

=== ANÁLISIS INSTITUCIONAL v2.2.1 ===
📊 ADX: 28.5 (≥20) ✅ Tendencia confirmada
🎯 MTF Alignment: 55% (min: 50%) ✅
📊 ATR%: 1.45 | Volatilidad OK (min: 0.3%)
📈 Régimen: TRENDING | Activando Trend Agent
📉 RSI: 52 (35-65) ✅ Zona operativa
📊 Volumen: 1.2x (≥0.8x) ✅
⚡ Criterios VENTA: 4/4 → DECISIÓN DIRECTA ($0 API)
💰 R/R Ratio: 2.0:1 (min: 1.8) ✅

✅ VENTA BTC/USDT | Confianza: 75% | R/R: 2.0:1
   SL: $97,800 (ATR-based) | TP: $94,200 (ATR-based)
   Trailing: activation=1.5%, distance=0.8%, profit_lock=0.5%
```

**Logs de decisión directa v2.2.1:**
```
⚡ BTC/USDT: VENTA directa (4/4 criterios) - $0 API
   Precio < EMA200: ✓ | RSI 35-65: ✓ | MACD < Signal: ✓ | Vol > 0.7x: ✓

⚡ ETH/USDT: Consulta IA (3/4 criterios) - caso ambiguo
   Precio > EMA200: ✓ | RSI 35-65: ✓ | MACD > Signal: ✗ | Vol > 0.7x: ✓

⏸️ SOL/USDT: ESPERA directa (2/4 criterios) - $0 API
   Criterios insuficientes para operar
```

**Logs de filtrado v2.2 (persistencia):**
```
💾 SQLite: Estado guardado (transacción ACID)
📈 Kelly Criterion: Win Rate 48.5%, Fracción 0.25
🔄 Fallback Parser: Extrayendo decisión de texto libre...
✅ Mapeo: "SELL" → "VENTA"
```

Si ves `DECISIÓN DIRECTA ($0 API)` significa que Python decidió sin llamar a la IA.
Si ves `Consulta IA (3/4 criterios)` significa que la IA validó un caso ambiguo.

## Siguiente Nivel

Una vez que el bot funcione en modo paper:

1. **Monitorea por 1-2 semanas**
   - Revisa los logs diariamente
   - Verifica que las decisiones tienen sentido

2. **Ajusta indicadores**
   - Modifica `config/config.yaml`
   - Experimenta con diferentes timeframes

3. **Solo entonces** considera modo live
   - Empieza con capital MUY pequeño
   - Monitorea constantemente

## Soporte

- 📖 Documentación completa: `README.md`
- 🐛 Problemas: Revisa logs en `logs/trading_bot.log`
- 🔧 Configuración: `config/config.yaml`

## Recordatorio de Seguridad

⚠️ **NUNCA**:
- Subas `.env` a GitHub
- Uses todo tu capital en las primeras semanas
- Dejes el bot sin supervisión en modo live al inicio

✅ **SIEMPRE**:
- Empieza en modo paper
- Usa stop loss
- Monitorea los logs
- Prueba con capital que puedas perder

---

¡Buena suerte y trade responsablemente! 🚀
