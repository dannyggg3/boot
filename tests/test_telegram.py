#!/usr/bin/env python3
"""
Script de prueba para verificar configuración de Telegram.
Ejecutar: python test_telegram.py
"""

import os
import asyncio
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_telegram():
    """Prueba el envío de mensaje a Telegram."""

    # Obtener credenciales
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

    print("=" * 50)
    print("TEST DE CONFIGURACION TELEGRAM")
    print("=" * 50)

    # Verificar credenciales
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN no configurado en .env")
        return False

    if not chat_id:
        print("TELEGRAM_CHAT_ID no configurado en .env")
        return False

    print(f"Bot Token: {bot_token[:10]}...{bot_token[-5:]}")
    print(f"Chat ID: {chat_id}")
    print("-" * 50)

    try:
        from telegram import Bot
        print("python-telegram-bot instalado correctamente")
    except ImportError:
        print("ERROR: python-telegram-bot no instalado")
        print("Ejecuta: pip install python-telegram-bot")
        return False

    # Enviar mensaje de prueba
    async def send_test():
        bot = Bot(token=bot_token)

        message = """
🧪 <b>TEST DE SATH BOT</b>

Si recibes este mensaje, Telegram está configurado correctamente.

✅ Bot Token: OK
✅ Chat ID: OK
✅ Conexión: OK

El bot enviará alertas aquí cuando:
• Se ejecute una operación
• Se active el kill switch
• Ocurra un error crítico
"""

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            print(f"ERROR enviando mensaje: {e}")
            return False

    # Ejecutar
    print("Enviando mensaje de prueba...")
    result = asyncio.run(send_test())

    if result:
        print("-" * 50)
        print("EXITO! Revisa tu Telegram")
        print("=" * 50)
        return True
    else:
        print("-" * 50)
        print("FALLO! Verifica las credenciales")
        print("=" * 50)
        return False


if __name__ == "__main__":
    test_telegram()
