# Guía de Inicio Rápido

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

# Opción 1: DeepSeek (Económico)
DEEPSEEK_API_KEY=sk-tu-clave-aqui

# Opción 2: OpenAI (Potente)
OPENAI_API_KEY=sk-tu-clave-aqui

# Opción 3: Gemini (Gratis con límites)
GEMINI_API_KEY=AIzaSy-tu-clave-aqui
```

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
- Revisa los logs: `tail -f logs/trading_bot.log`

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
