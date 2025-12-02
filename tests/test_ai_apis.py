#!/usr/bin/env python3
"""
Script de Prueba de APIs de IA
===============================
Verifica que las credenciales de DeepSeek y OpenAI funcionen correctamente
antes de ejecutar el bot de trading.
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import time

# Cargar variables de entorno
load_dotenv()

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Imprime un encabezado estilizado."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text:^70}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*70}{Colors.RESET}\n")


def print_success(text):
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text):
    """Imprime mensaje de error."""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_warning(text):
    """Imprime mensaje de advertencia."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_info(text):
    """Imprime mensaje informativo."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def test_deepseek():
    """
    Prueba la API de DeepSeek.
    """
    print_header("PRUEBA DE DEEPSEEK API")

    api_key = os.getenv('DEEPSEEK_API_KEY')

    if not api_key:
        print_error("DEEPSEEK_API_KEY no encontrada en .env")
        print_info("Agrega tu clave en .env: DEEPSEEK_API_KEY=sk-...")
        return False

    print_info(f"API Key encontrada: {api_key[:10]}...{api_key[-4:]}")

    try:
        # Inicializar cliente
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        print_info("Enviando petición de prueba a DeepSeek...")

        # Prompt de prueba relacionado con trading
        test_prompt = """
Eres un analista financiero experto. Responde en formato JSON:

Pregunta: ¿Cuál es la señal si el RSI está en 25 y el precio está por encima de la EMA 200?

Responde en este formato JSON:
{
    "señal": "COMPRA o VENTA o ESPERA",
    "razonamiento": "explicación breve"
}
"""

        start_time = time.time()

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente experto en análisis técnico de trading. Respondes siempre en formato JSON válido."
                },
                {
                    "role": "user",
                    "content": test_prompt
                }
            ],
            temperature=0.1,
            max_tokens=200
        )

        elapsed_time = time.time() - start_time

        # Obtener respuesta
        content = response.choices[0].message.content

        print_success("DeepSeek respondió correctamente!")
        print(f"\n{Colors.BOLD}Respuesta de DeepSeek:{Colors.RESET}")
        print(f"{Colors.CYAN}{content}{Colors.RESET}")

        print(f"\n{Colors.BOLD}Métricas:{Colors.RESET}")
        print(f"  • Tiempo de respuesta: {elapsed_time:.2f}s")
        print(f"  • Tokens usados: {response.usage.total_tokens}")
        print(f"  • Modelo: {response.model}")

        return True

    except Exception as e:
        print_error(f"Error al conectar con DeepSeek: {str(e)}")

        if "401" in str(e) or "Unauthorized" in str(e):
            print_warning("La API Key parece ser inválida")
            print_info("Verifica tu clave en: https://platform.deepseek.com/")
        elif "429" in str(e):
            print_warning("Límite de rate excedido")
            print_info("Espera unos minutos e intenta de nuevo")
        elif "insufficient" in str(e).lower():
            print_warning("Créditos insuficientes")
            print_info("Verifica tu balance en: https://platform.deepseek.com/")

        return False


def test_openai():
    """
    Prueba la API de OpenAI.
    """
    print_header("PRUEBA DE OPENAI API")

    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print_error("OPENAI_API_KEY no encontrada en .env")
        print_info("Agrega tu clave en .env: OPENAI_API_KEY=sk-...")
        return False

    print_info(f"API Key encontrada: {api_key[:10]}...{api_key[-4:]}")

    try:
        # Inicializar cliente
        client = OpenAI(api_key=api_key)

        print_info("Enviando petición de prueba a OpenAI...")

        # Prompt de prueba relacionado con trading
        test_prompt = """
Eres un analista financiero experto. Responde en formato JSON:

Pregunta: Si el MACD cruza por encima de la señal y el volumen aumenta, ¿qué indica?

Responde en este formato JSON:
{
    "señal": "COMPRA o VENTA o ESPERA",
    "razonamiento": "explicación breve"
}
"""

        start_time = time.time()

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Modelo más económico para pruebas
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente experto en análisis técnico de trading. Respondes siempre en formato JSON válido."
                },
                {
                    "role": "user",
                    "content": test_prompt
                }
            ],
            temperature=0.1,
            max_tokens=200
        )

        elapsed_time = time.time() - start_time

        # Obtener respuesta
        content = response.choices[0].message.content

        print_success("OpenAI respondió correctamente!")
        print(f"\n{Colors.BOLD}Respuesta de OpenAI:{Colors.RESET}")
        print(f"{Colors.CYAN}{content}{Colors.RESET}")

        print(f"\n{Colors.BOLD}Métricas:{Colors.RESET}")
        print(f"  • Tiempo de respuesta: {elapsed_time:.2f}s")
        print(f"  • Tokens usados: {response.usage.total_tokens}")
        print(f"  • Modelo: {response.model}")

        return True

    except Exception as e:
        print_error(f"Error al conectar con OpenAI: {str(e)}")

        if "401" in str(e) or "Unauthorized" in str(e):
            print_warning("La API Key parece ser inválida")
            print_info("Verifica tu clave en: https://platform.openai.com/api-keys")
        elif "429" in str(e):
            print_warning("Límite de rate excedido")
            print_info("Espera unos minutos e intenta de nuevo")
        elif "insufficient_quota" in str(e).lower():
            print_warning("Créditos insuficientes")
            print_info("Verifica tu balance en: https://platform.openai.com/usage")

        return False


def test_market_analysis_simulation():
    """
    Simula un análisis de mercado real con la mejor API disponible.
    """
    print_header("SIMULACIÓN DE ANÁLISIS DE MERCADO")

    # Determinar qué API usar
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')

    if not deepseek_key and not openai_key:
        print_error("No hay ninguna API configurada")
        return False

    # Preferir DeepSeek (más económico)
    if deepseek_key:
        provider = "deepseek"
        client = OpenAI(
            api_key=deepseek_key,
            base_url="https://api.deepseek.com"
        )
        model = "deepseek-chat"
        print_info("Usando DeepSeek para la simulación")
    else:
        provider = "openai"
        client = OpenAI(api_key=openai_key)
        model = "gpt-4o-mini"
        print_info("Usando OpenAI para la simulación")

    # Datos de mercado simulados
    market_data = {
        "symbol": "BTC/USDT",
        "current_price": 45000,
        "rsi": 32,
        "ema_50": 44200,
        "ema_200": 42000,
        "macd": 150,
        "macd_signal": 100,
        "trend": "alcista - precio por encima de EMA 200",
        "volatility": "media"
    }

    prompt = f"""
Actúa como un trader institucional profesional.

Analiza estos datos del mercado BTC/USDT:
- Precio actual: ${market_data['current_price']}
- RSI (14): {market_data['rsi']} (sobrevendido: <30)
- EMA 50: ${market_data['ema_50']}
- EMA 200: ${market_data['ema_200']}
- MACD: {market_data['macd']} (Señal: {market_data['macd_signal']})
- Tendencia: {market_data['trend']}
- Volatilidad: {market_data['volatility']}

Responde SOLO en formato JSON:
{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0-1.0,
    "razonamiento": "explicación técnica breve",
    "stop_loss_sugerido": precio_numérico,
    "take_profit_sugerido": precio_numérico
}}
"""

    try:
        print_info("Analizando datos de mercado simulados...")
        print(f"\n{Colors.BOLD}Datos de Mercado:{Colors.RESET}")
        for key, value in market_data.items():
            print(f"  • {key}: {value}")

        start_time = time.time()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un trader experto que analiza mercados y responde siempre en formato JSON válido."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=500
        )

        elapsed_time = time.time() - start_time
        content = response.choices[0].message.content

        print_success(f"Análisis completado en {elapsed_time:.2f}s")
        print(f"\n{Colors.BOLD}{Colors.GREEN}Decisión de Trading:{Colors.RESET}")
        print(f"{Colors.CYAN}{content}{Colors.RESET}")

        # Intentar parsear el JSON
        import json
        try:
            decision_data = json.loads(content)
            print(f"\n{Colors.BOLD}Resumen:{Colors.RESET}")
            print(f"  • Decisión: {Colors.BOLD}{decision_data.get('decision', 'N/A')}{Colors.RESET}")
            print(f"  • Confianza: {decision_data.get('confidence', 'N/A')}")
            print(f"  • Stop Loss: ${decision_data.get('stop_loss_sugerido', 'N/A')}")
            print(f"  • Take Profit: ${decision_data.get('take_profit_sugerido', 'N/A')}")
        except:
            print_warning("La respuesta no es JSON válido (pero la API funciona)")

        return True

    except Exception as e:
        print_error(f"Error en la simulación: {str(e)}")
        return False


def main():
    """
    Ejecuta todas las pruebas.
    """
    print(f"""
{Colors.BOLD}{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              Prueba de APIs de Inteligencia Artificial       ║
║                                                               ║
║              DeepSeek & OpenAI API Tester                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

    results = {
        'deepseek': False,
        'openai': False,
        'simulation': False
    }

    # Verificar archivo .env
    if not os.path.exists('.env'):
        print_error("Archivo .env no encontrado")
        print_info("Copia .env.example a .env y configura tus API keys")
        print_info("  cp .env.example .env")
        return 1

    print_info("Archivo .env encontrado")

    # Test DeepSeek
    if os.getenv('DEEPSEEK_API_KEY'):
        results['deepseek'] = test_deepseek()
    else:
        print_warning("DeepSeek API Key no configurada - saltando prueba")

    # Test OpenAI
    if os.getenv('OPENAI_API_KEY'):
        results['openai'] = test_openai()
    else:
        print_warning("OpenAI API Key no configurada - saltando prueba")

    # Simulación de análisis de mercado
    if results['deepseek'] or results['openai']:
        results['simulation'] = test_market_analysis_simulation()

    # Resumen final
    print_header("RESUMEN DE PRUEBAS")

    print(f"\n{Colors.BOLD}Resultados:{Colors.RESET}")

    if os.getenv('DEEPSEEK_API_KEY'):
        status = "✅ FUNCIONANDO" if results['deepseek'] else "❌ ERROR"
        color = Colors.GREEN if results['deepseek'] else Colors.RED
        print(f"  DeepSeek API:    {color}{status}{Colors.RESET}")

    if os.getenv('OPENAI_API_KEY'):
        status = "✅ FUNCIONANDO" if results['openai'] else "❌ ERROR"
        color = Colors.GREEN if results['openai'] else Colors.RED
        print(f"  OpenAI API:      {color}{status}{Colors.RESET}")

    if results['simulation']:
        print(f"  Simulación:      {Colors.GREEN}✅ EXITOSA{Colors.RESET}")

    # Recomendación
    print(f"\n{Colors.BOLD}Recomendación para el Bot:{Colors.RESET}")

    if results['deepseek']:
        print(f"  {Colors.GREEN}→ Usa DeepSeek (más económico y rápido){Colors.RESET}")
        print(f"    En config.yaml: ai_provider: \"deepseek\"")
    elif results['openai']:
        print(f"  {Colors.YELLOW}→ Usa OpenAI (más potente pero costoso){Colors.RESET}")
        print(f"    En config.yaml: ai_provider: \"openai\"")
    else:
        print(f"  {Colors.RED}→ Configura al menos una API antes de usar el bot{Colors.RESET}")

    # Siguiente paso
    if any(results.values()):
        print(f"\n{Colors.BOLD}{Colors.GREEN}🚀 Siguiente paso:{Colors.RESET}")
        print(f"  python main.py")
        return 0
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}⚠️  Configura tus API keys en .env antes de continuar{Colors.RESET}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Prueba interrumpida por el usuario{Colors.RESET}")
        sys.exit(1)
