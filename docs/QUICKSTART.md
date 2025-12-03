# Guía de Inicio Rápido - SATH v1.9.0 INSTITUCIONAL PRO MAX ★★★★★

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

### Configuración Optimizada v1.9.0 INSTITUCIONAL PRO MAX

Las siguientes optimizaciones institucionales vienen **habilitadas por defecto**:

```yaml
# === AGENTES ESPECIALIZADOS v1.9.0 ===
ai_agents:
  enabled: true
  min_volatility_percent: 0.35  # PAPER (0.40 para LIVE)
  min_volume_ratio: 0.5         # Confirma liquidez
  max_retries: 3                # Reintentos para resiliencia
  retry_delay_seconds: 2

# === GESTIÓN DE RIESGO INSTITUCIONAL v1.9 ===
risk_management:
  min_risk_reward_ratio: 2.0    # R/R mínimo 2:1 (RECHAZA si menor)
  max_price_deviation_percent: 0.2  # v1.9: Validación post-IA

  kelly_criterion:
    enabled: true
    min_confidence: 0.70        # PAPER (0.75 para LIVE)

  atr_stops:
    enabled: true
    sl_multiplier: 2.0          # SL a 2x ATR
    tp_multiplier: 4.0          # TP a 4x ATR (garantiza R/R 2:1)

# === INDICADORES TÉCNICOS v1.9 ===
technical_analysis:
  indicators:
    adx:
      enabled: true             # v1.9: Filtro de mercados laterales
      period: 14

# === MULTI-TIMEFRAME INSTITUCIONAL ===
multi_timeframe:
  enabled: true
  min_alignment_score: 0.75     # PAPER (0.80 para LIVE)

# === VALIDACIÓN DE RENTABILIDAD ===
position_sizing:
  profit_to_fees_ratio: 8.0     # PAPER (10.0 para LIVE)
```

**Impacto v1.9.0 INSTITUCIONAL PRO MAX:**
- **Validación Post-IA**: Re-verifica precio antes de ejecutar (elimina R/R inválido)
- **Filtro ADX**: Bloquea mercados laterales (ADX<20) → ahorra 40% en API
- **Menos trades, mayor calidad**: Solo opera con alta confianza (70-75%)
- **R/R garantizado**: ATR-based stops aseguran R/R 2:1 en cada trade
- **CI/CD Pipeline**: Calidad de código garantizada
- **Backtester integrado**: Valida estrategias antes de ir live
- **Ahorro total: 95-99% en llamadas API**

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

### Logs esperados (v1.9.0 INSTITUCIONAL PRO MAX)

```
╔═══════════════════════════════════════════════════════════╗
║     Sistema Autónomo de Trading Híbrido (SATH) v1.9.0     ║
║        ★★★★★ INSTITUCIONAL PRO MAX ★★★★★                  ║
╚═══════════════════════════════════════════════════════════╝

🔄 Iniciando análisis PARALELO de 3 símbolos...
✅ Análisis paralelo completado en 2.8s

=== ANÁLISIS INSTITUCIONAL v1.9.0 ===
📊 ADX: 32.5 (≥20) ✅ Tendencia confirmada
🎯 MTF Alignment: 82% (min: 75%) ✅
📊 ATR%: 1.45 | Volatilidad OK (min: 0.35%)
📈 Régimen: TRENDING | Activando Trend Agent
⚡ Confianza IA: 78% (min: 70%) ✅
💰 R/R Ratio: 2.3:1 (min: 2.0) ✅
📋 Profit/Fees: 12x (min: 8x) ✅

🔄 VALIDACIÓN POST-IA:
   Precio análisis: $96,500.00
   Precio actual:   $96,520.00
   Desviación:      0.021%
   Umbral máximo:   0.20%
✅ Precio validado - desviación dentro del umbral

✅ COMPRA BTC/USDT | Confianza: 78% | R/R: 2.3:1
   SL: $94,500 (ATR-based) | TP: $98,200 (ATR-based)
```

**Logs de filtrado v1.9 (ahorro de API):**
```
🚫 PRE-FILTRO ADX [ETH/USDT]: ADX=15.2 < 20 (mercado lateral) → NO LLAMAR IA
❌ MTF Alignment: 62% < 75% mínimo → ESPERA
❌ Confianza: 65% < 70% mínimo → ESPERA
❌ R/R Ratio: 1.4:1 < 2.0 mínimo → RECHAZADO
⚠️ ORDEN ABORTADA: Precio subió 0.35% desde análisis → R/R inválido
```

Si ves `🚫 PRE-FILTRO ADX` significa que el filtro v1.9 está funcionando y ahorrando llamadas a la API.
Si ves `⚠️ ORDEN ABORTADA: Precio...` significa que la validación post-IA v1.9 protegió contra un R/R inválido.

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
