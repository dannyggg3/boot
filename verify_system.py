#!/usr/bin/env python3
"""
SATH v2.2 - Script de Verificacion del Sistema
==============================================
Verifica que todo el sistema este listo para operar.

Uso:
    python verify_system.py [config_file]

Ejemplo:
    python verify_system.py config/config_paper.yaml
"""

import sys
import os
import time
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_result(name: str, success: bool, details: str = ""):
    status = "OK" if success else "FAIL"
    icon = "[OK]" if success else "[X]"
    print(f"  {icon} {name}: {status}")
    if details:
        print(f"      {details}")


def check_dependencies():
    """Verifica que todas las dependencias esten instaladas."""
    print_header("1. VERIFICANDO DEPENDENCIAS")

    required = [
        ('yaml', 'pyyaml'),
        ('ccxt', 'ccxt'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('openai', 'openai'),
        ('ta', 'ta'),
        ('dotenv', 'python-dotenv'),
    ]

    optional = [
        ('pydantic', 'pydantic'),
        ('influxdb_client', 'influxdb-client'),
        ('websockets', 'websockets'),
    ]

    all_ok = True

    print("\n  Dependencias requeridas:")
    for module, package in required:
        try:
            __import__(module)
            print_result(f"  {package}", True)
        except ImportError:
            print_result(f"  {package}", False, f"pip install {package}")
            all_ok = False

    print("\n  Dependencias opcionales:")
    for module, package in optional:
        try:
            __import__(module)
            print_result(f"  {package}", True)
        except ImportError:
            print_result(f"  {package}", False, "(opcional)")

    return all_ok


def check_config(config_path: str):
    """Verifica la configuracion."""
    print_header("2. VERIFICANDO CONFIGURACION")

    import yaml

    if not os.path.exists(config_path):
        print_result("Archivo config", False, f"No existe: {config_path}")
        return False, None

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print_result("Archivo config", True, config_path)
    except Exception as e:
        print_result("Archivo config", False, str(e))
        return False, None

    # Verificar campos criticos
    checks = [
        ('trading.mode', config.get('trading', {}).get('mode')),
        ('trading.symbols', config.get('trading', {}).get('symbols')),
        ('risk_management.initial_capital', config.get('risk_management', {}).get('initial_capital')),
        ('ai_provider', config.get('ai_provider')),
    ]

    all_ok = True
    for field, value in checks:
        if value:
            print_result(f"  {field}", True, str(value)[:50])
        else:
            print_result(f"  {field}", False, "No configurado")
            all_ok = False

    return all_ok, config


def check_env_vars():
    """Verifica variables de entorno."""
    print_header("3. VERIFICANDO VARIABLES DE ENTORNO")

    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        'DEEPSEEK_API_KEY',
        'BINANCE_TESTNET_API_KEY',
        'BINANCE_TESTNET_API_SECRET',
    ]

    optional_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'OPENAI_API_KEY',
    ]

    all_ok = True

    print("\n  Variables requeridas:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." + value[-4:] if len(value) > 15 else "***"
            print_result(f"  {var}", True, masked)
        else:
            print_result(f"  {var}", False, "No configurada")
            all_ok = False

    print("\n  Variables opcionales:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print_result(f"  {var}", True)
        else:
            print_result(f"  {var}", False, "(opcional)")

    return all_ok


def check_exchange_connection(config: dict):
    """Verifica conexion al exchange."""
    print_header("4. VERIFICANDO CONEXION AL EXCHANGE")

    try:
        from engines.market_engine import MarketEngine

        # Crear market engine con config
        import tempfile
        import yaml

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            temp_config = f.name

        engine = MarketEngine(temp_config)
        os.unlink(temp_config)

        # Verificar conexion
        if engine.connection:
            exchange_name = getattr(engine, 'exchange_name', engine.connection.name if engine.connection else 'Unknown')
            print_result("Conexion exchange", True, exchange_name)

            # Obtener balance
            try:
                balance = engine.get_balance()
                usdt = balance.get('USDT', 0)
                print_result("  Balance USDT", True, f"${usdt:.2f}")
            except Exception as e:
                print_result("  Balance USDT", False, str(e))

            # Obtener precio de BTC
            try:
                price = engine.get_current_price('BTC/USDT')
                print_result("  Precio BTC/USDT", True, f"${price:,.2f}")
            except Exception as e:
                print_result("  Precio BTC/USDT", False, str(e))

            return True
        else:
            print_result("Conexion exchange", False, "No se pudo conectar")
            return False

    except Exception as e:
        print_result("Conexion exchange", False, str(e))
        return False


def check_database():
    """Verifica la base de datos SQLite."""
    print_header("5. VERIFICANDO BASE DE DATOS")

    import sqlite3

    databases = [
        ('data/positions.db', 'Posiciones'),
        ('data/risk_manager.db', 'Risk Manager'),
    ]

    all_ok = True

    for db_path, name in databases:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                print_result(f"{name}", True, f"{len(tables)} tablas")
            except Exception as e:
                print_result(f"{name}", False, str(e))
                all_ok = False
        else:
            print_result(f"{name}", True, "Se creara al iniciar")

    return all_ok


def check_ai_connection(config: dict):
    """Verifica conexion a la IA."""
    print_header("6. VERIFICANDO CONEXION IA")

    provider = config.get('ai_provider', 'deepseek')
    model = config.get('ai_model', 'deepseek-chat')

    print(f"  Provider: {provider}")
    print(f"  Model: {model}")

    try:
        from openai import OpenAI

        if provider == 'deepseek':
            api_key = os.getenv('DEEPSEEK_API_KEY')
            base_url = "https://api.deepseek.com"
        else:
            api_key = os.getenv('OPENAI_API_KEY')
            base_url = None

        if not api_key:
            print_result("API Key", False, "No configurada")
            return False

        client = OpenAI(api_key=api_key, base_url=base_url)

        # Hacer una llamada simple de prueba
        start = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Responde solo: OK"}],
            max_tokens=10,
            temperature=0
        )
        latency = (time.time() - start) * 1000

        content = response.choices[0].message.content
        print_result("Conexion IA", True, f"{latency:.0f}ms")
        print_result("  Respuesta", True, content[:50])

        return True

    except Exception as e:
        print_result("Conexion IA", False, str(e))
        return False


def check_directories():
    """Verifica y crea directorios necesarios."""
    print_header("7. VERIFICANDO DIRECTORIOS")

    directories = ['data', 'logs', 'config']

    for dir_name in directories:
        if os.path.exists(dir_name):
            print_result(dir_name, True, "Existe")
        else:
            try:
                os.makedirs(dir_name, exist_ok=True)
                print_result(dir_name, True, "Creado")
            except Exception as e:
                print_result(dir_name, False, str(e))

    return True


def show_config_summary(config: dict):
    """Muestra resumen de la configuracion."""
    print_header("8. RESUMEN DE CONFIGURACION")

    trading = config.get('trading', {})
    risk = config.get('risk_management', {})
    position = config.get('position_management', {})

    print(f"""
  MODO: {trading.get('mode', 'N/A').upper()}

  Trading:
    - Symbols: {', '.join(trading.get('symbols', []))}
    - Timeframe: {trading.get('timeframe', 'N/A')}
    - Scan interval: {trading.get('scan_interval', 'N/A')}s

  Riesgo:
    - Capital inicial: ${risk.get('initial_capital', 0):,}
    - Max risk/trade: {risk.get('max_risk_per_trade', 0)}%
    - Max drawdown diario: {risk.get('max_daily_drawdown', 0)}%
    - R/R minimo: {risk.get('min_risk_reward_ratio', 0)}:1
    - Kelly: {'ON' if risk.get('kelly_criterion', {}).get('enabled') else 'OFF'}
    - ATR Stops: {'ON' if risk.get('atr_stops', {}).get('enabled') else 'OFF'}

  Posiciones:
    - Max posiciones: {position.get('portfolio', {}).get('max_concurrent_positions', 0)}
    - Max exposicion: {position.get('portfolio', {}).get('max_exposure_percent', 0)}%
    - Trailing stop: {'ON' if position.get('trailing_stop', {}).get('enabled') else 'OFF'}

  IA:
    - Provider: {config.get('ai_provider', 'N/A')}
    - Model fast: {config.get('ai_model_fast', 'N/A')}
    - Model deep: {config.get('ai_model_deep', 'N/A')}
    - Hybrid: {'ON' if config.get('ai_use_hybrid_analysis') else 'OFF'}
""")


def run_test_analysis(config: dict):
    """Ejecuta un analisis de prueba."""
    print_header("9. ANALISIS DE PRUEBA")

    try:
        from engines.ai_engine import AIEngine
        from engines.market_engine import MarketEngine
        from modules.technical_analysis import TechnicalAnalyzer

        import tempfile
        import yaml

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            temp_config = f.name

        print("  Inicializando componentes...")
        market_engine = MarketEngine(temp_config)
        ai_engine = AIEngine(temp_config)
        tech_analyzer = TechnicalAnalyzer(config)

        os.unlink(temp_config)

        symbol = config.get('trading', {}).get('symbols', ['BTC/USDT'])[0]
        timeframe = config.get('trading', {}).get('timeframe', '15m')

        print(f"  Obteniendo datos de {symbol} ({timeframe})...")
        ohlcv = market_engine.get_historical_data(symbol, timeframe=timeframe, limit=150)

        if not ohlcv:
            print_result("Datos OHLCV", False, "No se obtuvieron datos")
            return False

        print_result("Datos OHLCV", True, f"{len(ohlcv)} velas")

        print("  Calculando indicadores tecnicos...")
        tech_data = tech_analyzer.analyze(ohlcv)

        if not tech_data:
            print_result("Indicadores", False, "Error calculando")
            return False

        print_result("Indicadores", True)
        print(f"      RSI: {tech_data.get('rsi', 'N/A'):.2f}")
        print(f"      ADX: {tech_data.get('adx', 'N/A'):.2f}")
        print(f"      EMA50: ${tech_data.get('ema_50', 0):,.2f}")
        print(f"      Precio: ${tech_data.get('current_price', 0):,.2f}")

        print("\n  Ejecutando pre-filtro local...")
        tech_data['symbol'] = symbol

        # Simular pre-filtro
        adx = tech_data.get('adx', 0)
        min_adx = config.get('ai_agents', {}).get('min_adx_trend', 20)

        if adx < min_adx:
            print(f"      Pre-filtro: RECHAZADO (ADX {adx:.1f} < {min_adx})")
            print(f"      Ahorro: No se llamo a la IA ($0)")
        else:
            print(f"      Pre-filtro: PASADO (ADX {adx:.1f} >= {min_adx})")
            print("      El sistema llamaria a la IA para analisis completo")

        return True

    except Exception as e:
        print_result("Analisis de prueba", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def main():
    print("""
    ================================================================
     SATH v2.2 - VERIFICACION DEL SISTEMA
    ================================================================
     Sistema Autonomo de Trading Hibrido
     Verificacion pre-operacion
    ================================================================
    """)

    # Determinar archivo de config
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = 'config/config_paper.yaml'

    print(f"  Config: {config_path}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # 1. Dependencias
    results['deps'] = check_dependencies()

    # 2. Configuracion
    config_ok, config = check_config(config_path)
    results['config'] = config_ok

    if not config:
        print("\n[ERROR] No se pudo cargar la configuracion. Abortando.")
        return 1

    # 3. Variables de entorno
    results['env'] = check_env_vars()

    # 4. Directorios
    results['dirs'] = check_directories()

    # 5. Base de datos
    results['db'] = check_database()

    # 6. Exchange
    results['exchange'] = check_exchange_connection(config)

    # 7. IA
    results['ai'] = check_ai_connection(config)

    # 8. Resumen config
    show_config_summary(config)

    # 9. Analisis de prueba
    results['test'] = run_test_analysis(config)

    # Resumen final
    print_header("RESULTADO FINAL")

    all_passed = all(results.values())

    if all_passed:
        print("""
    ================================================================
     SISTEMA LISTO PARA OPERAR
    ================================================================
     Todos los checks pasaron correctamente.

     Para iniciar el bot:
       python main.py

     O con config especifica:
       SATH_CONFIG=config/config_paper.yaml python main.py
    ================================================================
        """)
        return 0
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"""
    ================================================================
     SISTEMA NO LISTO - CORREGIR ERRORES
    ================================================================
     Checks fallidos: {', '.join(failed)}

     Revisa los errores arriba y corrigelos antes de operar.
    ================================================================
        """)
        return 1


if __name__ == "__main__":
    sys.exit(main())
