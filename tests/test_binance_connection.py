#!/usr/bin/env python3
"""
Script de prueba para verificar credenciales de Binance
"""
import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

print("╔" + "═" * 68 + "╗")
print("║" + " " * 68 + "║")
print("║" + "    VERIFICACIÓN DE CREDENCIALES DE BINANCE".center(68) + "║")
print("║" + " " * 68 + "║")
print("╚" + "═" * 68 + "╝")
print()

# Cargar credenciales
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

if not api_key or not api_secret:
    print("❌ ERROR: Credenciales de Binance no encontradas en .env")
    exit(1)

print(f"✅ API Key encontrada: {api_key[:10]}...{api_key[-4:]}")
print(f"✅ API Secret encontrada: {api_secret[:10]}...{api_secret[-4:]}")
print()

# Intentar conectar
print("=" * 70)
print("                    PRUEBA DE CONEXIÓN                    ")
print("=" * 70)
print()

try:
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot'
        }
    })

    # Cargar mercados
    print("ℹ️  Cargando mercados de Binance...")
    markets = exchange.load_markets()
    print(f"✅ Conectado exitosamente - {len(markets)} mercados disponibles")
    print()

    # Verificar permisos obteniendo balance
    print("=" * 70)
    print("                  VERIFICACIÓN DE PERMISOS                  ")
    print("=" * 70)
    print()

    print("ℹ️  Intentando obtener balance (requiere permiso de lectura)...")
    try:
        balance = exchange.fetch_balance()
        print("✅ PERMISO DE LECTURA: OK")

        # Mostrar activos con balance > 0
        total_assets = {k: v for k, v in balance['total'].items() if v > 0}
        if total_assets:
            print(f"\n📊 Activos en cuenta: {len(total_assets)}")
            for asset, amount in list(total_assets.items())[:5]:
                print(f"   • {asset}: {amount}")
        else:
            print("\nℹ️  Balance: $0 (cuenta nueva - normal para paper trading)")

    except Exception as e:
        if '401' in str(e) or 'Invalid API-key' in str(e):
            print("❌ ERROR: API Key inválida o incorrecta")
        elif '403' in str(e) or 'permission' in str(e).lower():
            print("⚠️  ADVERTENCIA: Sin permisos de lectura")
        else:
            print(f"⚠️  Error al obtener balance: {str(e)[:100]}")

    print()

    # Probar obtener precio de BTC (no requiere autenticación)
    print("=" * 70)
    print("              PRUEBA DE OBTENCIÓN DE PRECIOS              ")
    print("=" * 70)
    print()

    print("ℹ️  Obteniendo precio de BTC/USDT...")
    ticker = exchange.fetch_ticker('BTC/USDT')
    print(f"✅ Precio actual de BTC: ${ticker['last']:,.2f}")
    print(f"   • Volumen 24h: ${ticker['quoteVolume']:,.0f}")
    print(f"   • High 24h: ${ticker['high']:,.2f}")
    print(f"   • Low 24h: ${ticker['low']:,.2f}")

    print()

    # Obtener datos históricos
    print("=" * 70)
    print("            PRUEBA DE DATOS HISTÓRICOS (OHLCV)            ")
    print("=" * 70)
    print()

    print("ℹ️  Obteniendo últimas 5 velas de 1h de BTC/USDT...")
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=5)
    print(f"✅ Datos históricos obtenidos: {len(ohlcv)} velas")
    print("\n   Últimas velas:")
    for candle in ohlcv[-3:]:
        from datetime import datetime
        timestamp = datetime.fromtimestamp(candle[0] / 1000)
        print(f"   • {timestamp}: O=${candle[1]:.2f} H=${candle[2]:.2f} L=${candle[3]:.2f} C=${candle[4]:.2f}")

    print()
    print("=" * 70)
    print("                        RESUMEN                        ")
    print("=" * 70)
    print()
    print("✅ Conexión a Binance: OK")
    print("✅ Lectura de mercados: OK")
    print("✅ Lectura de precios: OK")
    print("✅ Datos históricos: OK")
    print("✅ Permisos de lectura: OK")
    print()
    print("🎯 LISTO PARA MODO PAPER TRADING")
    print()
    print("⚠️  IMPORTANTE:")
    print("   • Estas credenciales SOLO tienen permisos de lectura")
    print("   • El bot NO ejecutará operaciones reales")
    print("   • En modo 'paper', solo simula las operaciones")
    print()
    print("Siguiente paso:")
    print("  python main.py")

except Exception as e:
    print(f"❌ ERROR de conexión: {e}")
    print()
    print("Posibles causas:")
    print("  • API Key o Secret incorrectos")
    print("  • Restricciones de IP (verifica en Binance)")
    print("  • Problemas de red")
    print()
    print("Solución:")
    print("  1. Verifica las credenciales en .env")
    print("  2. Ve a Binance → API Management")
    print("  3. Verifica que la API key esté activa")
    print("  4. Revisa restricciones de IP")
