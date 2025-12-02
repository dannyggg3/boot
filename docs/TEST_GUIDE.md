# Guía de Prueba de APIs

Este documento explica cómo probar tus credenciales de DeepSeek y OpenAI antes de ejecutar el bot.

## Script de Prueba: `test_ai_apis.py`

### ¿Qué hace este script?

✅ Verifica que tus API keys sean válidas
✅ Prueba la conexión con DeepSeek y/o OpenAI
✅ Simula un análisis de mercado real
✅ Muestra tiempos de respuesta y uso de tokens
✅ Te recomienda qué proveedor usar

## Cómo Usar

### 1. Configurar tus API Keys

Edita el archivo `.env` y agrega tus credenciales:

```env
# DeepSeek (Recomendado - más económico)
DEEPSEEK_API_KEY=sk-tu-clave-aqui

# OpenAI (Opcional - más potente)
OPENAI_API_KEY=sk-tu-clave-aqui
```

### 2. Ejecutar el Test

```bash
python test_ai_apis.py
```

## Salida Esperada

### ✅ Todo Funciona

```
╔═══════════════════════════════════════════════════════════════╗
║              Prueba de APIs de Inteligencia Artificial       ║
╚═══════════════════════════════════════════════════════════════╝

===============================================================
                    PRUEBA DE DEEPSEEK API
===============================================================

ℹ️  API Key encontrada: sk-abc123...xyz9
ℹ️  Enviando petición de prueba a DeepSeek...
✅ DeepSeek respondió correctamente!

Respuesta de DeepSeek:
{
    "señal": "COMPRA",
    "razonamiento": "RSI sobrevendido indica posible rebote..."
}

Métricas:
  • Tiempo de respuesta: 1.2s
  • Tokens usados: 145
  • Modelo: deepseek-chat

===============================================================
                  SIMULACIÓN DE ANÁLISIS DE MERCADO
===============================================================

Datos de Mercado:
  • symbol: BTC/USDT
  • current_price: 45000
  • rsi: 32 (sobrevendido)
  • ema_50: 44200
  • trend: alcista

✅ Análisis completado en 1.5s

Decisión de Trading:
{
    "decision": "COMPRA",
    "confidence": 0.75,
    "razonamiento": "RSI sobrevendido en tendencia alcista...",
    "stop_loss_sugerido": 43500,
    "take_profit_sugerido": 48000
}

===============================================================
                      RESUMEN DE PRUEBAS
===============================================================

Resultados:
  DeepSeek API:    ✅ FUNCIONANDO
  OpenAI API:      ✅ FUNCIONANDO
  Simulación:      ✅ EXITOSA

Recomendación para el Bot:
  → Usa DeepSeek (más económico y rápido)
    En config.yaml: ai_provider: "deepseek"

🚀 Siguiente paso:
  python main.py
```

## Posibles Errores

### ❌ API Key Inválida

```
❌ Error al conectar con DeepSeek: 401 Unauthorized
⚠️  La API Key parece ser inválida
ℹ️  Verifica tu clave en: https://platform.deepseek.com/
```

**Solución:**
1. Verifica que copiaste la API key completa (empieza con `sk-`)
2. Asegúrate de que no tiene espacios al inicio o final
3. Genera una nueva key si es necesario

### ❌ Créditos Insuficientes

```
⚠️  Créditos insuficientes
ℹ️  Verifica tu balance en: https://platform.deepseek.com/
```

**Solución:**
1. Verifica tu balance en el dashboard
2. Recarga créditos si es necesario
3. O usa la otra API (DeepSeek/OpenAI)

### ❌ Rate Limit Excedido

```
⚠️  Límite de rate excedido
ℹ️  Espera unos minutos e intenta de nuevo
```

**Solución:**
- Espera 1-2 minutos y vuelve a ejecutar el script

### ⚠️ API Key No Configurada

```
⚠️  DeepSeek API Key no configurada - saltando prueba
```

**Solución:**
- Agrega la API key en el archivo `.env`

## Obtener API Keys

### DeepSeek (Recomendado)

1. Visita: https://platform.deepseek.com/
2. Crea una cuenta o inicia sesión
3. Ve a "API Keys"
4. Genera una nueva key
5. Cópiala a `.env` como `DEEPSEEK_API_KEY`

**Ventajas:**
- Muy económico (≈$0.14 por millón de tokens)
- Rápido (1-2 segundos de respuesta)
- Excelente para trading algorítmico

### OpenAI

1. Visita: https://platform.openai.com/
2. Crea una cuenta
3. Ve a "API Keys"
4. Genera una nueva key
5. Cópiala a `.env` como `OPENAI_API_KEY`

**Ventajas:**
- Muy potente (GPT-4)
- Mejor razonamiento complejo

**Desventajas:**
- Más costoso
- Requiere configurar billing

## Comparación de Costos (estimado)

Por **1,000 análisis de mercado**:

| Proveedor | Costo Aproximado | Velocidad |
|-----------|------------------|-----------|
| DeepSeek  | $0.50 - $1       | 1-2s      |
| OpenAI (GPT-4o-mini) | $2 - $4 | 1-3s |
| OpenAI (GPT-4) | $15 - $30 | 2-4s |

## Preguntas Frecuentes

### ¿Necesito ambas APIs?

**No.** Solo necesitas UNA de las dos. DeepSeek es suficiente y más económico.

### ¿Puedo cambiar de API después?

**Sí.** Solo cambia `ai_provider` en `config/config.yaml`:

```yaml
ai_provider: "deepseek"  # o "openai"
```

### ¿Cuántos créditos necesito?

Para **1 mes de trading** (analizando cada hora):
- DeepSeek: ~$5-10
- OpenAI: ~$20-50

### ¿El bot gasta créditos en modo paper?

**Sí.** El bot consulta a la IA incluso en modo paper (para generar decisiones), pero NO ejecuta operaciones reales.

## Siguiente Paso

Si el test fue exitoso:

```bash
python main.py
```

El bot empezará a analizar el mercado y simular operaciones (modo paper).

---

**Soporte:**
- DeepSeek: https://platform.deepseek.com/
- OpenAI: https://platform.openai.com/docs
