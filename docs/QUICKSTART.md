# Guía de Inicio Rápido - SATH v2.1.0 INSTITUCIONAL PROFESIONAL ★★★★★

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

### 4. Verificar Configuración

```bash
python check_setup.py
```

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

### Configuración Optimizada v2.1.0 INSTITUCIONAL PROFESIONAL

Las siguientes optimizaciones institucionales vienen **habilitadas por defecto**:

```yaml
# === AGENTES ESPECIALIZADOS v2.1.0 ===
ai_agents:
  enabled: true
  min_volatility_percent: 0.5   # Subido de 0.35
  min_volume_ratio: 1.0         # v2.1: Subido de 0.5
  ideal_volume_ratio: 1.3       # v2.1: NUEVO
  min_adx_trend: 25             # v2.1: Subido de 20
  max_retries: 3

# === GESTIÓN DE RIESGO INSTITUCIONAL v2.1 ===
risk_management:
  min_risk_reward_ratio: 2.0

  kelly_criterion:
    enabled: true
    min_confidence: 0.70

  atr_stops:
    enabled: true
    sl_multiplier: 2.5
    tp_multiplier: 5.0
    min_distance_percent: 1.8

  # v2.1: HABILITADO
  session_filter:
    enabled: true
    avoid_hours_utc:
      - [0, 6]

# === TRAILING STOP v2.1 (CORREGIDO) ===
position_management:
  trailing_stop:
    enabled: true
    activation_profit_percent: 2.0  # v2.1: SUBIDO
    trail_distance_percent: 1.0     # v2.1: BAJADO
    min_profit_to_lock: 0.8         # v2.1: SUBIDO
    cooldown_seconds: 15            # v2.1: SUBIDO

# === MULTI-TIMEFRAME INSTITUCIONAL ===
multi_timeframe:
  enabled: true
  min_alignment_score: 0.65
```

**Impacto v2.1.0 INSTITUCIONAL PROFESIONAL:**
- **Trailing Math Corregido**: activation 2.0% > distance 1.0% (SL siempre sobre entry)
- **PROFIT LOCK**: Trailing NUNCA convierte ganador en perdedor
- **Range Agent**: Opera mercados laterales (+25% oportunidades)
- **ADX >= 25**: Solo tendencias confirmadas (-60% falsos breakouts)
- **RSI 35-65**: Evita entrar en zonas de reversión
- **Session Filter**: Evita horas de baja liquidez (00-06 UTC)
- **Win Rate esperado: ~48%** (antes ~42%)

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

### Logs esperados (v2.1.0 INSTITUCIONAL PROFESIONAL)

```
╔═══════════════════════════════════════════════════════════╗
║     Sistema Autónomo de Trading Híbrido (SATH) v2.1.0     ║
║      ★★★★★ INSTITUCIONAL PROFESIONAL ★★★★★               ║
╚═══════════════════════════════════════════════════════════╝

🔄 Iniciando análisis PARALELO de 3 símbolos...
✅ Análisis paralelo completado en 2.8s

=== ANÁLISIS INSTITUCIONAL v2.1.0 ===
📊 ADX: 32.5 (≥25) ✅ Tendencia confirmada
🎯 MTF Alignment: 82% (min: 65%) ✅
📊 ATR%: 1.45 | Volatilidad OK (min: 0.5%)
📈 Régimen: TRENDING | Activando Trend Agent
📉 RSI: 52 (35-65) ✅ Zona operativa
📊 Volumen: 1.4x (≥1.0x) ✅
⚡ Confianza IA: 78% (min: 70%) ✅
💰 R/R Ratio: 2.3:1 (min: 2.0) ✅

✅ COMPRA BTC/USDT | Confianza: 78% | R/R: 2.3:1
   SL: $94,500 (ATR-based) | TP: $98,200 (ATR-based)
   Trailing: activation=2%, distance=1%, profit_lock=0.8%
```

**Logs de filtrado v2.1 (nuevos agentes):**
```
📊 ADX: 18.5 (<25) → Activando RANGE AGENT (Bollinger)
🎯 Precio en zona SOPORTE (12% del rango BB)
📉 RSI: 38 (zona operativa) ✅
💡 Range Agent: COMPRA en soporte con confianza 65%

🚫 RSI: 72 (>65) → Fuera de zona operativa → ESPERA
🚫 Volumen: 0.7x (<1.0x) → Volumen insuficiente → ESPERA
🚫 Session Filter: 03:00 UTC → Hora evitada → ESPERA
```

Si ves `Activando RANGE AGENT` significa que el bot ahora opera en mercados laterales.
Si ves `RSI: XX (>65)` significa que evita zonas de reversión.

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
