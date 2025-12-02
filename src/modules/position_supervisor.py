"""
Position Supervisor - Agente IA para supervisión de posiciones
==============================================================
Supervisa posiciones abiertas periódicamente y toma decisiones
de ajuste: HOLD, TIGHTEN_SL, EXTEND_TP.

Autor: Trading Bot System
Versión: 1.5
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

from schemas.position_schemas import (
    Position,
    SupervisorDecision,
    SupervisorAction,
    PositionSide
)

load_dotenv()
logger = logging.getLogger(__name__)


class PositionSupervisor:
    """
    Agente IA que supervisa posiciones abiertas y recomienda ajustes.

    Acciones permitidas (modo moderado):
    - HOLD: Mantener sin cambios
    - TIGHTEN_SL: Acercar stop loss (asegurar ganancias)
    - EXTEND_TP: Mover take profit más lejos

    NO incluye PARTIAL_CLOSE ni FULL_CLOSE (modo conservador).
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el supervisor de posiciones.

        Args:
            config: Configuración del bot con sección position_management
        """
        self.config = config
        self.enabled = config.get('position_management', {}).get('supervision', {}).get('enabled', True)

        # Acciones permitidas (modo moderado por defecto)
        supervision_config = config.get('position_management', {}).get('supervision', {})
        self.allowed_actions = supervision_config.get('actions_allowed', ['HOLD', 'TIGHTEN_SL', 'EXTEND_TP'])
        self.check_interval = supervision_config.get('check_interval_seconds', 60)

        # Configuración de IA
        self.provider = config.get('ai_provider', 'deepseek')
        self.model = config.get('ai_model_fast', config.get('ai_model', 'deepseek-chat'))

        self.client = None
        self._initialize_ai_client()

        logger.info(f"Position Supervisor inicializado (enabled={self.enabled})")
        logger.info(f"Acciones permitidas: {self.allowed_actions}")

    def _initialize_ai_client(self):
        """Inicializa el cliente de IA."""
        try:
            if self.provider == 'deepseek':
                api_key = os.getenv('DEEPSEEK_API_KEY')
                if api_key:
                    self.client = OpenAI(
                        api_key=api_key,
                        base_url="https://api.deepseek.com"
                    )
            elif self.provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    self.client = OpenAI(api_key=api_key)

            if self.client:
                logger.info(f"Supervisor AI client inicializado: {self.provider}")
            else:
                logger.warning("No se pudo inicializar cliente de IA para supervisor")

        except Exception as e:
            logger.error(f"Error inicializando AI client para supervisor: {e}")

    def supervise_position(
        self,
        position: Position,
        current_price: float,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SupervisorDecision:
        """
        Supervisa una posición abierta y recomienda una acción.

        Args:
            position: Posición a supervisar
            current_price: Precio actual del mercado
            market_data: Datos técnicos opcionales (RSI, tendencia, etc.)

        Returns:
            SupervisorDecision con la acción recomendada
        """
        if not self.enabled:
            return SupervisorDecision(
                action=SupervisorAction.HOLD,
                reasoning="Supervisión deshabilitada",
                confidence=1.0
            )

        # Si no hay cliente de IA, usar lógica local básica
        if not self.client:
            return self._local_supervision(position, current_price)

        try:
            # Calcular métricas de la posición
            pnl_data = position.calculate_pnl(current_price)
            rr_data = position.get_risk_reward_current(current_price)

            # Construir prompt para el supervisor
            prompt = self._build_supervision_prompt(
                position=position,
                current_price=current_price,
                pnl_data=pnl_data,
                rr_data=rr_data,
                market_data=market_data
            )

            # Obtener decisión de IA
            response = self._call_ai(prompt)

            if response:
                decision = self._parse_supervisor_response(response, position, current_price)
                return decision

            # Fallback a supervisión local si IA falla
            return self._local_supervision(position, current_price)

        except Exception as e:
            logger.error(f"Error en supervisión de posición {position.id}: {e}")
            return SupervisorDecision(
                action=SupervisorAction.HOLD,
                reasoning=f"Error en supervisión: {str(e)}",
                confidence=0.0
            )

    def _build_supervision_prompt(
        self,
        position: Position,
        current_price: float,
        pnl_data: Dict[str, Any],
        rr_data: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Construye el prompt para el supervisor de IA."""

        # Información de mercado opcional
        market_context = ""
        if market_data:
            market_context = f"""
=== CONDICIONES DE MERCADO ACTUALES ===
RSI: {market_data.get('rsi', 'N/A')}
Tendencia: {market_data.get('trend_analysis', 'N/A')}
Volatilidad: {market_data.get('volatility_level', 'N/A')}
MACD: {market_data.get('macd', 'N/A')} (Señal: {market_data.get('macd_signal', 'N/A')})
"""

        # Calcular distancias porcentuales
        sl_distance_pct = abs(current_price - position.stop_loss) / current_price * 100
        tp_distance_pct = abs(position.take_profit - current_price) / current_price * 100 if position.take_profit else 0

        # Tiempo en posición
        hold_time = datetime.now() - position.entry_time
        hold_minutes = int(hold_time.total_seconds() / 60)

        prompt = f"""
Eres un SUPERVISOR DE POSICIONES profesional. Tu trabajo es monitorear posiciones abiertas y recomendar ajustes CONSERVADORES.

=== POSICIÓN ACTUAL ===
ID: {position.id}
Símbolo: {position.symbol}
Lado: {position.side}
Entrada: ${position.entry_price:,.2f}
Cantidad: {position.quantity}
Tiempo abierta: {hold_minutes} minutos

=== ESTADO ACTUAL ===
Precio Actual: ${current_price:,.2f}
P&L: ${pnl_data['pnl']:,.2f} ({pnl_data['pnl_percent']:+.2f}%)
{'🟢 EN GANANCIA' if pnl_data['is_profitable'] else '🔴 EN PÉRDIDA'}

=== PROTECCIÓN ACTUAL ===
Stop Loss: ${position.stop_loss:,.2f} (distancia: {sl_distance_pct:.2f}%)
Take Profit: ${f'{position.take_profit:,.2f}' if position.take_profit else 'N/A'} {f'(distancia: {tp_distance_pct:.2f}%)' if position.take_profit else ''}
SL Original: ${position.initial_stop_loss:,.2f}
Trailing Activo: {'Sí' if position.trailing_stop_active else 'No'}

=== RIESGO/BENEFICIO ACTUAL ===
Riesgo hasta SL: ${rr_data['risk']:,.4f}
Beneficio hasta TP: ${rr_data['reward']:,.4f}
Ratio R:R: {rr_data['ratio']:.2f}
{market_context}
=== ACCIONES PERMITIDAS ===
{', '.join(self.allowed_actions)}

REGLAS DE DECISIÓN:
1. HOLD: Si la posición está evolucionando bien, no tocar
2. TIGHTEN_SL: Si hay ganancias significativas (>1.5%), considerar mover SL para asegurar parte
   - NUNCA mover SL a pérdida si ya está en ganancia
   - Mover SL gradualmente (no más de 30-50% de la ganancia)
3. EXTEND_TP: Si el momentum es muy fuerte y el precio se acerca al TP, considerar extenderlo
   - Solo si la tendencia sigue siendo favorable

IMPORTANTE:
- Sé CONSERVADOR. Es mejor mantener (HOLD) que ajustar innecesariamente
- Si P&L es negativo, NO muevas el SL más lejos (eso aumenta el riesgo)
- Si hay duda, siempre HOLD

Responde SOLO en JSON:
{{
    "action": "{self.allowed_actions[0] if self.allowed_actions else 'HOLD'}",
    "new_stop_loss": null,
    "new_take_profit": null,
    "reasoning": "Explicación breve de tu decisión",
    "confidence": 0.0-1.0
}}

Donde "action" debe ser UNA de: {self.allowed_actions}
Si action es TIGHTEN_SL, incluye "new_stop_loss" con el nuevo precio
Si action es EXTEND_TP, incluye "new_take_profit" con el nuevo precio
"""
        return prompt

    def _call_ai(self, prompt: str) -> Optional[str]:
        """Llama al modelo de IA para supervisión."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un supervisor de posiciones profesional. Respondes SOLO en JSON válido. Eres conservador y cauteloso."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error llamando IA para supervisión: {e}")
            return None

    def _parse_supervisor_response(
        self,
        response_text: str,
        position: Position,
        current_price: float
    ) -> SupervisorDecision:
        """Parsea la respuesta del supervisor de IA."""
        try:
            data = json.loads(response_text)

            # Validar acción
            action_str = data.get('action', 'HOLD').upper()
            if action_str not in self.allowed_actions:
                logger.warning(f"Acción {action_str} no permitida, usando HOLD")
                action_str = 'HOLD'

            action = SupervisorAction(action_str)

            # Extraer nuevos precios si aplica
            new_sl = data.get('new_stop_loss')
            new_tp = data.get('new_take_profit')

            # Validar nuevos precios
            if action == SupervisorAction.TIGHTEN_SL and new_sl:
                new_sl = self._validate_new_stop_loss(position, current_price, new_sl)

            if action == SupervisorAction.EXTEND_TP and new_tp:
                new_tp = self._validate_new_take_profit(position, current_price, new_tp)

            return SupervisorDecision(
                action=action,
                new_stop_loss=new_sl,
                new_take_profit=new_tp,
                reasoning=data.get('reasoning', 'Sin razonamiento'),
                confidence=float(data.get('confidence', 0.5))
            )

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta de supervisor: {e}")
            return SupervisorDecision(
                action=SupervisorAction.HOLD,
                reasoning="Error parseando respuesta de IA",
                confidence=0.0
            )

    def _validate_new_stop_loss(
        self,
        position: Position,
        current_price: float,
        new_sl: float
    ) -> Optional[float]:
        """Valida que el nuevo SL sea válido y más favorable."""
        try:
            new_sl = float(new_sl)

            if position.side == PositionSide.LONG or position.side == "long":
                # Para LONG, nuevo SL debe ser mayor que el actual (más ajustado)
                # pero menor que el precio actual
                if new_sl > position.stop_loss and new_sl < current_price:
                    return new_sl
                else:
                    logger.warning(f"Nuevo SL {new_sl} inválido para LONG (actual: {position.stop_loss}, precio: {current_price})")
                    return None
            else:
                # Para SHORT, nuevo SL debe ser menor que el actual
                # pero mayor que el precio actual
                if new_sl < position.stop_loss and new_sl > current_price:
                    return new_sl
                else:
                    logger.warning(f"Nuevo SL {new_sl} inválido para SHORT")
                    return None

        except (ValueError, TypeError):
            return None

    def _validate_new_take_profit(
        self,
        position: Position,
        current_price: float,
        new_tp: float
    ) -> Optional[float]:
        """Valida que el nuevo TP sea válido y más lejano."""
        try:
            new_tp = float(new_tp)

            if not position.take_profit:
                # Si no había TP, cualquier valor válido es aceptable
                if position.side == PositionSide.LONG or position.side == "long":
                    return new_tp if new_tp > current_price else None
                else:
                    return new_tp if new_tp < current_price else None

            if position.side == PositionSide.LONG or position.side == "long":
                # Para LONG, nuevo TP debe ser mayor que el actual
                if new_tp > position.take_profit and new_tp > current_price:
                    return new_tp
            else:
                # Para SHORT, nuevo TP debe ser menor que el actual
                if new_tp < position.take_profit and new_tp < current_price:
                    return new_tp

            return None

        except (ValueError, TypeError):
            return None

    def _local_supervision(
        self,
        position: Position,
        current_price: float
    ) -> SupervisorDecision:
        """
        Supervisión local basada en reglas simples (fallback si IA no disponible).
        """
        pnl_data = position.calculate_pnl(current_price)
        pnl_percent = pnl_data['pnl_percent']

        # Regla 1: Si ganancia > 2%, considerar ajustar SL al breakeven
        if pnl_percent >= 2.0 and not position.trailing_stop_active:
            # Mover SL al punto de entrada (breakeven)
            new_sl = position.entry_price

            # Verificar que sea un movimiento válido
            if position.side == PositionSide.LONG or position.side == "long":
                if new_sl > position.stop_loss:
                    return SupervisorDecision(
                        action=SupervisorAction.TIGHTEN_SL,
                        new_stop_loss=new_sl,
                        reasoning=f"Ganancia de {pnl_percent:.1f}% - moviendo SL a breakeven para proteger capital",
                        confidence=0.8
                    )
            else:
                if new_sl < position.stop_loss:
                    return SupervisorDecision(
                        action=SupervisorAction.TIGHTEN_SL,
                        new_stop_loss=new_sl,
                        reasoning=f"Ganancia de {pnl_percent:.1f}% - moviendo SL a breakeven para proteger capital",
                        confidence=0.8
                    )

        # Regla 2: Si ganancia > 3% y ya está en breakeven, ajustar SL para asegurar 1%
        if pnl_percent >= 3.0:
            if position.stop_loss >= position.entry_price if (position.side == PositionSide.LONG or position.side == "long") else position.stop_loss <= position.entry_price:
                # Calcular nuevo SL que asegure 1% de ganancia
                if position.side == PositionSide.LONG or position.side == "long":
                    new_sl = position.entry_price * 1.01  # 1% sobre entrada
                    if new_sl > position.stop_loss and new_sl < current_price:
                        return SupervisorDecision(
                            action=SupervisorAction.TIGHTEN_SL,
                            new_stop_loss=new_sl,
                            reasoning=f"Ganancia de {pnl_percent:.1f}% - asegurando 1% de ganancia mínima",
                            confidence=0.75
                        )
                else:
                    new_sl = position.entry_price * 0.99  # 1% bajo entrada
                    if new_sl < position.stop_loss and new_sl > current_price:
                        return SupervisorDecision(
                            action=SupervisorAction.TIGHTEN_SL,
                            new_stop_loss=new_sl,
                            reasoning=f"Ganancia de {pnl_percent:.1f}% - asegurando 1% de ganancia mínima",
                            confidence=0.75
                        )

        # Default: HOLD
        return SupervisorDecision(
            action=SupervisorAction.HOLD,
            reasoning=f"Posición evolucionando normalmente (P&L: {pnl_percent:+.2f}%)",
            confidence=0.9
        )

    def supervise_all_positions(
        self,
        positions: List[Position],
        prices: Dict[str, float],
        market_data_map: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Supervisa múltiples posiciones y retorna recomendaciones.

        Args:
            positions: Lista de posiciones abiertas
            prices: Diccionario {symbol: current_price}
            market_data_map: Diccionario {symbol: market_data} opcional

        Returns:
            Lista de decisiones con position_id y recomendación
        """
        results = []

        for position in positions:
            current_price = prices.get(position.symbol)
            if not current_price:
                logger.warning(f"No hay precio para {position.symbol}, saltando supervisión")
                continue

            market_data = None
            if market_data_map:
                market_data = market_data_map.get(position.symbol)

            decision = self.supervise_position(position, current_price, market_data)

            results.append({
                'position_id': position.id,
                'symbol': position.symbol,
                'decision': decision
            })

            # Log de la decisión
            if decision.action != SupervisorAction.HOLD:
                logger.info(f"[{position.symbol}] Supervisión recomienda {decision.action.value}: {decision.reasoning}")

        return results

    def get_supervision_summary(
        self,
        decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Genera un resumen de las decisiones de supervisión.

        Args:
            decisions: Lista de decisiones de supervise_all_positions

        Returns:
            Resumen con estadísticas
        """
        summary = {
            'total_positions': len(decisions),
            'holds': 0,
            'tighten_sl': 0,
            'extend_tp': 0,
            'actions_needed': []
        }

        for item in decisions:
            decision = item['decision']

            if decision.action == SupervisorAction.HOLD:
                summary['holds'] += 1
            elif decision.action == SupervisorAction.TIGHTEN_SL:
                summary['tighten_sl'] += 1
                summary['actions_needed'].append({
                    'position_id': item['position_id'],
                    'symbol': item['symbol'],
                    'action': 'TIGHTEN_SL',
                    'new_stop_loss': decision.new_stop_loss,
                    'reasoning': decision.reasoning
                })
            elif decision.action == SupervisorAction.EXTEND_TP:
                summary['extend_tp'] += 1
                summary['actions_needed'].append({
                    'position_id': item['position_id'],
                    'symbol': item['symbol'],
                    'action': 'EXTEND_TP',
                    'new_take_profit': decision.new_take_profit,
                    'reasoning': decision.reasoning
                })

        return summary


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)

    # Config de prueba
    test_config = {
        'ai_provider': 'deepseek',
        'ai_model_fast': 'deepseek-chat',
        'position_management': {
            'supervision': {
                'enabled': True,
                'check_interval_seconds': 60,
                'actions_allowed': ['HOLD', 'TIGHTEN_SL', 'EXTEND_TP']
            }
        }
    }

    supervisor = PositionSupervisor(test_config)

    # Crear posición de prueba
    test_position = Position(
        id="test123",
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        entry_price=95000.0,
        quantity=0.01,
        stop_loss=93000.0,
        take_profit=100000.0,
        initial_stop_loss=93000.0
    )

    # Simular precio actual (en ganancia)
    current_price = 97000.0

    # Supervisar
    decision = supervisor.supervise_position(test_position, current_price)

    print("\n=== RESULTADO SUPERVISIÓN ===")
    print(f"Acción: {decision.action.value}")
    print(f"Razonamiento: {decision.reasoning}")
    print(f"Confianza: {decision.confidence}")
    if decision.new_stop_loss:
        print(f"Nuevo SL: ${decision.new_stop_loss:,.2f}")
    if decision.new_take_profit:
        print(f"Nuevo TP: ${decision.new_take_profit:,.2f}")
