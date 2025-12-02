"""
Position Schemas - Modelos de datos para gestión de posiciones
==============================================================
Define los esquemas Pydantic para posiciones, órdenes y trade history.
Permite validación robusta y serialización a/desde SQLite.

Autor: Trading Bot System
Versión: 1.5
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class PositionStatus(str, Enum):
    """Estados posibles de una posición."""
    PENDING = "pending"      # Orden de entrada enviada, esperando fill
    OPEN = "open"            # Posición abierta con protección activa
    CLOSING = "closing"      # Cerrando posición (SL/TP triggered)
    CLOSED = "closed"        # Posición cerrada completamente


class PositionSide(str, Enum):
    """Lado de la posición."""
    LONG = "long"   # Compra (profit si precio sube)
    SHORT = "short" # Venta (solo en futuros, no disponible en SPOT)


class ExitReason(str, Enum):
    """Razón de cierre de posición."""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    AI_DECISION = "ai_decision"
    MANUAL = "manual"
    KILL_SWITCH = "kill_switch"
    ERROR = "error"


class OrderType(str, Enum):
    """Tipos de órdenes soportadas."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS_LIMIT = "stop_loss_limit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"
    OCO = "oco"


class OrderStatus(str, Enum):
    """Estados de una orden."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REJECTED = "rejected"


class SupervisorAction(str, Enum):
    """Acciones del agente supervisor de posiciones."""
    HOLD = "HOLD"                  # Mantener sin cambios
    TIGHTEN_SL = "TIGHTEN_SL"      # Mover SL más cerca (asegurar ganancias)
    EXTEND_TP = "EXTEND_TP"        # Mover TP más lejos
    PARTIAL_CLOSE = "PARTIAL_CLOSE"  # Cerrar parte de la posición
    FULL_CLOSE = "FULL_CLOSE"      # Cerrar toda la posición


# =============================================================================
# SCHEMAS PRINCIPALES
# =============================================================================

class PositionCreate(BaseModel):
    """Datos para crear una nueva posición."""
    symbol: str = Field(..., description="Par de trading (ej: BTC/USDT)")
    side: PositionSide = Field(..., description="Lado de la posición")
    entry_price: float = Field(..., gt=0, description="Precio de entrada")
    quantity: float = Field(..., gt=0, description="Cantidad")
    stop_loss: float = Field(..., gt=0, description="Precio de stop loss")
    take_profit: Optional[float] = Field(None, gt=0, description="Precio de take profit")

    # Metadata de entrada
    entry_order_id: Optional[str] = Field(None, description="ID de orden de entrada")
    confidence: float = Field(0.0, ge=0, le=1, description="Confianza de la IA al entrar")
    agent_type: str = Field("general", description="Agente que generó la señal")
    entry_reasoning: Optional[str] = Field(None, description="Razonamiento de entrada")


class Position(BaseModel):
    """Modelo completo de una posición."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str
    side: PositionSide
    status: PositionStatus = PositionStatus.OPEN

    # Entry details
    entry_price: float
    quantity: float
    entry_time: datetime = Field(default_factory=datetime.now)
    entry_order_id: Optional[str] = None
    confidence: float = 0.0
    agent_type: str = "general"
    entry_reasoning: Optional[str] = None

    # Protection levels
    stop_loss: float
    take_profit: Optional[float] = None
    initial_stop_loss: float = Field(default=0, description="SL original para tracking")
    trailing_stop_active: bool = False
    trailing_stop_distance: Optional[float] = None

    # OCO order tracking
    oco_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None

    # Exit details (filled when closed)
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    exit_order_id: Optional[str] = None

    # P&L
    realized_pnl: Optional[float] = None
    realized_pnl_percent: Optional[float] = None

    # Supervision history
    supervision_count: int = 0
    last_supervision: Optional[datetime] = None

    class Config:
        use_enum_values = True

    def calculate_pnl(self, current_price: float) -> dict:
        """Calcula P&L actual (unrealized) o final (realized)."""
        price = self.exit_price if self.exit_price else current_price

        if self.side == PositionSide.LONG or self.side == "long":
            pnl = (price - self.entry_price) * self.quantity
            pnl_percent = ((price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            pnl = (self.entry_price - price) * self.quantity
            pnl_percent = ((self.entry_price - price) / self.entry_price) * 100

        return {
            "pnl": round(pnl, 4),
            "pnl_percent": round(pnl_percent, 2),
            "is_profitable": pnl > 0
        }

    def get_risk_reward_current(self, current_price: float) -> dict:
        """Calcula R:R actual basado en precio corriente."""
        if self.side == PositionSide.LONG or self.side == "long":
            risk = current_price - self.stop_loss
            reward = (self.take_profit - current_price) if self.take_profit else 0
        else:
            risk = self.stop_loss - current_price
            reward = (current_price - self.take_profit) if self.take_profit else 0

        ratio = reward / risk if risk > 0 else 0

        return {
            "risk": round(risk, 4),
            "reward": round(reward, 4),
            "ratio": round(ratio, 2)
        }

    def should_trigger_trailing(self, current_price: float, activation_percent: float) -> bool:
        """Verifica si se debe activar trailing stop."""
        if self.trailing_stop_active:
            return False  # Ya está activo

        pnl = self.calculate_pnl(current_price)
        return pnl["pnl_percent"] >= activation_percent


class Order(BaseModel):
    """Modelo de una orden."""
    id: str
    position_id: Optional[str] = None
    symbol: str
    type: OrderType
    side: Literal["buy", "sell"]
    status: OrderStatus = OrderStatus.PENDING

    quantity: float
    price: Optional[float] = None  # Para limit orders
    stop_price: Optional[float] = None  # Para stop orders

    filled_quantity: float = 0
    average_fill_price: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None

    # OCO specific
    oco_id: Optional[str] = None
    oco_pair_id: Optional[str] = None

    # Exchange response
    exchange_response: Optional[dict] = None

    class Config:
        use_enum_values = True


class TradeResult(BaseModel):
    """Resultado de un trade cerrado (para historial)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    position_id: str
    symbol: str
    side: str

    entry_price: float
    exit_price: float
    quantity: float

    pnl: float
    pnl_percent: float
    result: Literal["win", "loss", "breakeven"]

    entry_time: datetime
    exit_time: datetime
    hold_time_minutes: int

    exit_reason: str
    agent_type: str
    confidence: float

    created_at: datetime = Field(default_factory=datetime.now)


class SupervisorDecision(BaseModel):
    """Decisión del agente supervisor de posiciones."""
    action: SupervisorAction
    new_stop_loss: Optional[float] = None
    new_take_profit: Optional[float] = None
    close_percent: Optional[float] = None  # Para PARTIAL_CLOSE
    reasoning: str
    confidence: float = Field(0.0, ge=0, le=1)

    class Config:
        use_enum_values = True


class PortfolioExposure(BaseModel):
    """Exposición actual del portfolio."""
    total_exposure_usd: float = 0
    position_count: int = 0
    max_single_exposure: float = 0
    exposure_percent: float = 0
    symbols_held: List[str] = []

    # Limits
    max_positions_allowed: int = 3
    max_exposure_allowed_percent: float = 50

    # Validation
    can_open_new_position: bool = True
    rejection_reason: Optional[str] = None


# =============================================================================
# SCHEMAS PARA API / CONFIG
# =============================================================================

class PositionManagementConfig(BaseModel):
    """Configuración de gestión de posiciones."""
    enabled: bool = True
    protection_mode: Literal["oco", "local"] = "oco"

    # OCO settings
    oco_sl_limit_buffer_percent: float = 0.2

    # Local monitoring settings
    local_check_interval_ms: int = 500

    # Trailing stop
    trailing_enabled: bool = True
    trailing_activation_percent: float = 1.0
    trailing_distance_percent: float = 2.0

    # AI Supervision
    supervision_enabled: bool = True
    supervision_interval_seconds: int = 60
    supervision_actions_allowed: List[str] = ["HOLD", "TIGHTEN_SL", "EXTEND_TP"]

    # Portfolio limits
    max_concurrent_positions: int = 3
    max_exposure_percent: float = 50
    max_per_symbol_percent: float = 25

    # Database
    database_path: str = "data/positions.db"


# =============================================================================
# HELPERS
# =============================================================================

def position_to_dict(position: Position) -> dict:
    """Convierte Position a dict para SQLite."""
    return {
        "id": position.id,
        "symbol": position.symbol,
        "side": position.side if isinstance(position.side, str) else position.side.value,
        "status": position.status if isinstance(position.status, str) else position.status.value,
        "entry_price": position.entry_price,
        "quantity": position.quantity,
        "entry_time": position.entry_time.isoformat() if position.entry_time else None,
        "entry_order_id": position.entry_order_id,
        "confidence": position.confidence,
        "agent_type": position.agent_type,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "initial_stop_loss": position.initial_stop_loss,
        "trailing_stop_active": position.trailing_stop_active,
        "oco_order_id": position.oco_order_id,
        "sl_order_id": position.sl_order_id,
        "tp_order_id": position.tp_order_id,
        "exit_price": position.exit_price,
        "exit_time": position.exit_time.isoformat() if position.exit_time else None,
        "exit_reason": position.exit_reason if isinstance(position.exit_reason, str) else (position.exit_reason.value if position.exit_reason else None),
        "realized_pnl": position.realized_pnl,
        "realized_pnl_percent": position.realized_pnl_percent,
    }


def dict_to_position(data: dict) -> Position:
    """Convierte dict de SQLite a Position."""
    # Parse datetime strings
    if data.get("entry_time") and isinstance(data["entry_time"], str):
        data["entry_time"] = datetime.fromisoformat(data["entry_time"])
    if data.get("exit_time") and isinstance(data["exit_time"], str):
        data["exit_time"] = datetime.fromisoformat(data["exit_time"])

    return Position(**data)
