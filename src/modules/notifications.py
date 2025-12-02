"""
Notifications Module - Sistema de Alertas
==========================================
Envía notificaciones a Telegram cuando ocurren eventos importantes:
- Operaciones ejecutadas
- Kill switch activado
- Errores críticos
- Resumen diario

Autor: Trading Bot System
Versión: 1.0
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Intentar importar telegram
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Bot = None
    TelegramError = Exception


class NotificationManager:
    """
    Gestor de notificaciones que envía alertas a Telegram.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el gestor de notificaciones.

        Args:
            config: Configuración del bot
        """
        self.config = config
        notifications_config = config.get('notifications', {})
        telegram_config = notifications_config.get('telegram', {})

        self.enabled = telegram_config.get('enabled', False)
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

        self.bot: Optional[Bot] = None

        if self.enabled and TELEGRAM_AVAILABLE and self.bot_token and self.chat_id:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("Telegram NotificationManager inicializado")
            except Exception as e:
                logger.error(f"Error inicializando Telegram bot: {e}")
                self.enabled = False
        elif self.enabled and not TELEGRAM_AVAILABLE:
            logger.warning("Telegram habilitado pero python-telegram-bot no instalado")
            self.enabled = False
        elif self.enabled and (not self.bot_token or not self.chat_id):
            logger.warning("Telegram habilitado pero faltan credenciales (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)")
            self.enabled = False

    def _send_sync(self, message: str):
        """Envía mensaje de forma síncrona."""
        if not self.enabled or not self.bot:
            return

        try:
            # Crear nuevo event loop si no existe
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(self._send_async(message))
        except Exception as e:
            logger.error(f"Error enviando mensaje Telegram: {e}")

    async def _send_async(self, message: str):
        """Envía mensaje de forma asíncrona."""
        if not self.enabled or not self.bot:
            return

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.debug("Mensaje Telegram enviado")
        except TelegramError as e:
            logger.error(f"Error Telegram: {e}")

    def send(self, message: str):
        """
        Envía un mensaje a Telegram.

        Args:
            message: Mensaje a enviar (soporta HTML)
        """
        self._send_sync(message)

    # ==================== ALERTAS PREDEFINIDAS ====================

    def notify_trade_executed(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        confidence: float = 0.0
    ):
        """
        Notifica cuando se ejecuta una operación.
        """
        emoji = "🟢" if side.upper() == "BUY" else "🔴"
        side_text = "COMPRA" if side.upper() == "BUY" else "VENTA"

        message = f"""
{emoji} <b>OPERACIÓN EJECUTADA</b>

<b>Par:</b> {symbol}
<b>Tipo:</b> {side_text}
<b>Cantidad:</b> {amount:.8f}
<b>Precio:</b> ${price:,.2f}
<b>Stop Loss:</b> ${stop_loss:,.2f}
<b>Take Profit:</b> {f'${take_profit:,.2f}' if take_profit else 'N/A'}
<b>Confianza IA:</b> {confidence*100:.1f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_trade_closed(
        self,
        symbol: str,
        side: str,
        pnl: float,
        pnl_percent: float,
        reason: str = "Manual"
    ):
        """
        Notifica cuando se cierra una operación.
        """
        emoji = "💰" if pnl > 0 else "💸"
        status = "GANANCIA" if pnl > 0 else "PÉRDIDA"

        message = f"""
{emoji} <b>OPERACIÓN CERRADA - {status}</b>

<b>Par:</b> {symbol}
<b>Lado:</b> {side}
<b>PnL:</b> ${pnl:+,.2f} ({pnl_percent:+.2f}%)
<b>Razón:</b> {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_kill_switch(self, reason: str, capital: float, loss_percent: float):
        """
        Notifica cuando se activa el kill switch.
        """
        message = f"""
🚨🚨🚨 <b>KILL SWITCH ACTIVADO</b> 🚨🚨🚨

<b>Razón:</b> {reason}
<b>Capital actual:</b> ${capital:,.2f}
<b>Pérdida:</b> {loss_percent:.2f}%

⚠️ El bot ha detenido todas las operaciones.
Revisa tu cuenta inmediatamente.

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_error(self, error_type: str, error_message: str, symbol: str = "N/A"):
        """
        Notifica errores críticos.
        """
        message = f"""
❌ <b>ERROR CRÍTICO</b>

<b>Tipo:</b> {error_type}
<b>Símbolo:</b> {symbol}
<b>Mensaje:</b> {error_message[:200]}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_startup(self, mode: str, symbols: list, capital: float):
        """
        Notifica cuando el bot inicia.
        """
        symbols_text = ", ".join(symbols[:5])
        if len(symbols) > 5:
            symbols_text += f" (+{len(symbols)-5} más)"

        message = f"""
🤖 <b>SATH BOT INICIADO</b>

<b>Modo:</b> {mode.upper()}
<b>Capital:</b> ${capital:,.2f}
<b>Símbolos:</b> {symbols_text}

✅ Sistema operando normalmente

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_shutdown(self, reason: str = "Manual"):
        """
        Notifica cuando el bot se apaga.
        """
        message = f"""
🔴 <b>SATH BOT DETENIDO</b>

<b>Razón:</b> {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_daily_summary(
        self,
        trades_count: int,
        wins: int,
        losses: int,
        daily_pnl: float,
        total_pnl: float,
        capital: float
    ):
        """
        Envía resumen diario.
        """
        win_rate = (wins / trades_count * 100) if trades_count > 0 else 0
        emoji = "📈" if daily_pnl > 0 else "📉" if daily_pnl < 0 else "➖"

        message = f"""
{emoji} <b>RESUMEN DIARIO</b>

<b>Operaciones:</b> {trades_count}
<b>Ganadas:</b> {wins} | <b>Perdidas:</b> {losses}
<b>Win Rate:</b> {win_rate:.1f}%

<b>PnL Hoy:</b> ${daily_pnl:+,.2f}
<b>PnL Total:</b> ${total_pnl:+,.2f}
<b>Capital:</b> ${capital:,.2f}

⏰ {datetime.now().strftime('%Y-%m-%d')}
"""
        self.send(message)

    def notify_opportunity_detected(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        reason: str
    ):
        """
        Notifica cuando se detecta una oportunidad (antes de ejecutar).
        """
        emoji = "🟢" if signal == "COMPRA" else "🔴" if signal == "VENTA" else "⏸️"

        message = f"""
🔔 <b>OPORTUNIDAD DETECTADA</b>

<b>Par:</b> {symbol}
<b>Señal:</b> {emoji} {signal}
<b>Confianza:</b> {confidence*100:.1f}%
<b>Razón:</b> {reason[:150]}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    # ==================== v1.5: ALERTAS DE POSICIÓN ====================

    def notify_position_created(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: Optional[float],
        position_id: str
    ):
        """
        Notifica cuando se crea una posición con protección OCO.
        """
        emoji = "📈" if side.upper() == "LONG" else "📉"
        side_text = "LONG" if side.upper() == "LONG" else "SHORT"

        message = f"""
{emoji} <b>POSICIÓN ABIERTA CON PROTECCIÓN</b>

<b>ID:</b> {position_id}
<b>Par:</b> {symbol}
<b>Lado:</b> {side_text}
<b>Cantidad:</b> {quantity:.8f}
<b>Entrada:</b> ${entry_price:,.2f}

<b>🛡️ PROTECCIÓN ACTIVA:</b>
<b>Stop Loss:</b> ${stop_loss:,.2f}
<b>Take Profit:</b> {f'${take_profit:,.2f}' if take_profit else 'N/A'}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_sl_hit(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_percent: float,
        position_id: str
    ):
        """
        Notifica cuando se activa el Stop Loss.
        """
        message = f"""
🛑 <b>STOP LOSS EJECUTADO</b>

<b>ID:</b> {position_id}
<b>Par:</b> {symbol}
<b>Entrada:</b> ${entry_price:,.2f}
<b>Salida:</b> ${exit_price:,.2f}

<b>PnL:</b> ${pnl:+,.2f} ({pnl_percent:+.2f}%)

⚠️ Posición cerrada por protección de pérdida máxima

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_tp_hit(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_percent: float,
        position_id: str
    ):
        """
        Notifica cuando se alcanza el Take Profit.
        """
        message = f"""
🎯 <b>TAKE PROFIT ALCANZADO</b>

<b>ID:</b> {position_id}
<b>Par:</b> {symbol}
<b>Entrada:</b> ${entry_price:,.2f}
<b>Salida:</b> ${exit_price:,.2f}

<b>💰 PnL:</b> ${pnl:+,.2f} ({pnl_percent:+.2f}%)

✅ Objetivo de ganancia alcanzado

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_trailing_update(
        self,
        symbol: str,
        old_sl: float,
        new_sl: float,
        current_price: float,
        unrealized_pnl_percent: float,
        position_id: str
    ):
        """
        Notifica cuando se actualiza el trailing stop.
        """
        message = f"""
📈 <b>TRAILING STOP ACTUALIZADO</b>

<b>ID:</b> {position_id}
<b>Par:</b> {symbol}
<b>Precio actual:</b> ${current_price:,.2f}

<b>SL Anterior:</b> ${old_sl:,.2f}
<b>SL Nuevo:</b> ${new_sl:,.2f}

<b>PnL no realizado:</b> {unrealized_pnl_percent:+.2f}%

🔒 Ganancia parcial asegurada

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_ai_adjustment(
        self,
        symbol: str,
        action: str,
        reasoning: str,
        old_value: Optional[float],
        new_value: Optional[float],
        position_id: str
    ):
        """
        Notifica cuando la IA ajusta una posición.
        """
        action_emoji = {
            'TIGHTEN_SL': '🔒',
            'EXTEND_TP': '🎯',
            'HOLD': '⏸️',
            'PARTIAL_CLOSE': '✂️',
            'FULL_CLOSE': '🚪'
        }.get(action, '🤖')

        change_text = ""
        if old_value is not None and new_value is not None:
            change_text = f"\n<b>Anterior:</b> ${old_value:,.2f}\n<b>Nuevo:</b> ${new_value:,.2f}"

        message = f"""
{action_emoji} <b>AJUSTE IA DE POSICIÓN</b>

<b>ID:</b> {position_id}
<b>Par:</b> {symbol}
<b>Acción:</b> {action}
{change_text}

<b>Razonamiento:</b>
{reasoning[:200]}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_position_closed(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_percent: float,
        exit_reason: str,
        hold_time_minutes: int,
        position_id: str
    ):
        """
        Notifica cuando se cierra una posición completa con todos los detalles.
        """
        emoji = "💰" if pnl > 0 else "💸"
        result = "GANANCIA" if pnl > 0 else "PÉRDIDA" if pnl < 0 else "BREAKEVEN"

        # Formatear tiempo de hold
        if hold_time_minutes < 60:
            hold_text = f"{hold_time_minutes} minutos"
        elif hold_time_minutes < 1440:
            hold_text = f"{hold_time_minutes // 60}h {hold_time_minutes % 60}m"
        else:
            days = hold_time_minutes // 1440
            hours = (hold_time_minutes % 1440) // 60
            hold_text = f"{days}d {hours}h"

        message = f"""
{emoji} <b>POSICIÓN CERRADA - {result}</b>

<b>ID:</b> {position_id}
<b>Par:</b> {symbol}
<b>Lado:</b> {side.upper()}

<b>Entrada:</b> ${entry_price:,.2f}
<b>Salida:</b> ${exit_price:,.2f}
<b>Cantidad:</b> {quantity:.8f}

<b>PnL:</b> ${pnl:+,.2f} ({pnl_percent:+.2f}%)

<b>Razón de cierre:</b> {exit_reason}
<b>Tiempo en posición:</b> {hold_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def send_message(self, message: str):
        """
        Alias para send() - envía mensaje personalizado.
        """
        self.send(message)


# Singleton para uso global
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager(config: Dict[str, Any] = None) -> Optional[NotificationManager]:
    """
    Obtiene o crea la instancia del notification manager.

    Args:
        config: Configuración del bot (solo necesaria la primera vez)

    Returns:
        NotificationManager instance o None si no está configurado
    """
    global _notification_manager

    if _notification_manager is None and config is not None:
        _notification_manager = NotificationManager(config)

    return _notification_manager


if __name__ == "__main__":
    # Prueba del módulo
    logging.basicConfig(level=logging.INFO)

    test_config = {
        'notifications': {
            'telegram': {
                'enabled': True
            }
        }
    }

    notifier = NotificationManager(test_config)

    if notifier.enabled:
        notifier.notify_startup(
            mode="TEST",
            symbols=["BTC/USDT", "ETH/USDT"],
            capital=50.0
        )
        print("Notificación de prueba enviada")
    else:
        print("Telegram no está configurado correctamente")
        print(f"  - Token: {'✓' if notifier.bot_token else '✗'}")
        print(f"  - Chat ID: {'✓' if notifier.chat_id else '✗'}")
