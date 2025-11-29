#!/usr/bin/env python3
"""
Script de verificación de configuración del Trading Bot
Verifica que todas las dependencias y configuraciones estén correctas.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Verifica la versión de Python."""
    print("🔍 Verificando versión de Python...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Se requiere Python 3.9+")
        return False

def check_dependencies():
    """Verifica que las dependencias estén instaladas."""
    print("\n🔍 Verificando dependencias...")

    required_packages = {
        'yaml': 'pyyaml',
        'ccxt': 'ccxt',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'pandas_ta': 'pandas-ta',
        'dotenv': 'python-dotenv',
        'openai': 'openai',
    }

    all_installed = True

    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - Ejecuta: pip install {package}")
            all_installed = False

    return all_installed

def check_config_files():
    """Verifica que los archivos de configuración existan."""
    print("\n🔍 Verificando archivos de configuración...")

    required_files = {
        'config/config.yaml': 'Archivo de configuración principal',
        '.env': 'Variables de entorno (credenciales)',
    }

    all_exist = True

    for file_path, description in required_files.items():
        if Path(file_path).exists():
            print(f"   ✅ {file_path} - {description}")
        else:
            print(f"   ⚠️  {file_path} - {description} NO ENCONTRADO")
            if file_path == '.env':
                print(f"      💡 Copia .env.example a .env y configura tus credenciales")
            all_exist = False

    return all_exist

def check_directories():
    """Verifica que los directorios necesarios existan."""
    print("\n🔍 Verificando estructura de directorios...")

    required_dirs = [
        'src/engines',
        'src/modules',
        'config',
        'logs',
        'data',
    ]

    all_exist = True

    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"   ✅ {dir_path}/")
        else:
            print(f"   ❌ {dir_path}/ - NO EXISTE")
            all_exist = False

    return all_exist

def check_env_variables():
    """Verifica que las variables de entorno estén configuradas."""
    print("\n🔍 Verificando variables de entorno...")

    from dotenv import load_dotenv
    load_dotenv()

    # Verificar al menos una API key de IA
    ai_keys = {
        'DEEPSEEK_API_KEY': 'DeepSeek',
        'OPENAI_API_KEY': 'OpenAI',
        'GEMINI_API_KEY': 'Google Gemini'
    }

    has_ai_key = False
    for key, name in ai_keys.items():
        if os.getenv(key):
            print(f"   ✅ {name} API Key configurada")
            has_ai_key = True
        else:
            print(f"   ⚠️  {name} API Key no configurada")

    if not has_ai_key:
        print(f"   ❌ Se requiere al menos una API key de IA")
        return False

    # Verificar exchange keys (opcional)
    exchange_keys = {
        'BINANCE_API_KEY': 'Binance API Key',
        'BINANCE_API_SECRET': 'Binance Secret'
    }

    for key, name in exchange_keys.items():
        if os.getenv(key):
            print(f"   ✅ {name} configurada")
        else:
            print(f"   ℹ️  {name} no configurada (opcional si usas paper trading)")

    return True

def check_config_yaml():
    """Verifica que el config.yaml sea válido."""
    print("\n🔍 Verificando config.yaml...")

    try:
        import yaml

        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Verificar campos importantes
        required_fields = {
            'ai_provider': config.get('ai_provider'),
            'market_type': config.get('market_type'),
            'trading': config.get('trading'),
        }

        all_valid = True

        if config.get('ai_provider') in ['deepseek', 'openai', 'gemini']:
            print(f"   ✅ Proveedor de IA: {config['ai_provider']}")
        else:
            print(f"   ❌ Proveedor de IA inválido: {config.get('ai_provider')}")
            all_valid = False

        if config.get('market_type') in ['crypto', 'forex_stocks']:
            print(f"   ✅ Tipo de mercado: {config['market_type']}")
        else:
            print(f"   ❌ Tipo de mercado inválido: {config.get('market_type')}")
            all_valid = False

        if config.get('trading', {}).get('mode') in ['live', 'paper', 'backtest']:
            print(f"   ✅ Modo de trading: {config['trading']['mode']}")
        else:
            print(f"   ❌ Modo de trading inválido")
            all_valid = False

        return all_valid

    except Exception as e:
        print(f"   ❌ Error al leer config.yaml: {e}")
        return False

def main():
    """Ejecuta todas las verificaciones."""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║            Verificación de Configuración del Bot             ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    checks = [
        check_python_version(),
        check_dependencies(),
        check_config_files(),
        check_directories(),
        check_env_variables(),
        check_config_yaml(),
    ]

    print("\n" + "="*60)

    if all(checks):
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print("\n🚀 El bot está listo para ejecutarse!")
        print("\nPara iniciar el bot:")
        print("   python main.py")
        return 0
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        print("\n⚠️  Por favor corrige los problemas antes de ejecutar el bot")
        print("\nConsulta el README.md para más información:")
        print("   cat README.md")
        return 1

if __name__ == "__main__":
    sys.exit(main())
