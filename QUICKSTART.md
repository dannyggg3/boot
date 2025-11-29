# Guía de Inicio Rápido (v1.2)

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

### Configuración Optimizada v1.2

Las siguientes optimizaciones vienen **habilitadas por defecto**:

```yaml
# === AGENTES ESPECIALIZADOS (v1.2) ===
ai_agents:
  enabled: true
  min_volatility_percent: 0.5  # No opera si mercado "muerto"
  min_volume_ratio: 0.8

trading:
  # Análisis paralelo (4x más rápido)
  parallel_analysis: true

  # Protección anti-slippage
  price_verification:
    enabled: true
    max_deviation_percent: 0.5

  # Órdenes limit inteligentes
  order_execution:
    use_limit_orders: true
    max_slippage_percent: 0.3

  # Datos avanzados de mercado (v1.2)
  advanced_data:
    enabled: true
    order_book: true      # Muros de compra/venta
    funding_rate: true    # Sentimiento futuros
    open_interest: true   # Dinero en el mercado
    correlations: true    # Relación con BTC
```

**Impacto en costos v1.2:**
- Filtro de volatilidad: Ahorra ~70% en llamadas API
- Agentes especializados: Mejor precisión por estrategia
- Datos avanzados: Decisiones más informadas
- **Total: Ahorro del 90-97% vs. configuración básica**

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

### Logs esperados (v1.2)

```
🔄 Iniciando análisis PARALELO de 4 símbolos...
✅ Análisis paralelo completado en 3.2s

=== ANÁLISIS CON AGENTES ESPECIALIZADOS (v1.2) ===
ATR%: 1.45 | Volatilidad suficiente para operar
Régimen detectado: TRENDING
Activando Trend Agent...
Obteniendo datos avanzados: Order Book, Funding, OI...
✅ Decisión: COMPRA | Agente: trend | Confianza: 85%

✅ Verificación de precio OK: Desviación aceptable: 0.12%
Convirtiendo a orden LIMIT: precio=95234.50 (slippage=0.30%)
```

**Logs de filtrado (ahorro de API):**
```
ATR%: 0.35 | Volatilidad muy baja (< 0.5%)
⏸️ ESPERA: Mercado sin volatilidad - Ahorrando llamada a API
```

Si ves `⚠️ ORDEN ABORTADA: Precio subió 0.65%` significa que la protección anti-slippage está funcionando correctamente.

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
