"""
Router de control de bots.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from core.database import fetchrow, execute, fetch
from services.orchestrator import BotOrchestrator
from .users import get_current_user

router = APIRouter()
orchestrator = BotOrchestrator()

# Schemas
class BotConfig(BaseModel):
    mode: str = "paper"  # paper, live
    symbols: List[str] = ["BTC/USDT"]
    capital: float = 100.0
    scan_interval: int = 180
    max_positions: int = 1
    risk_per_trade: float = 0.02

class BotStatus(BaseModel):
    status: str
    mode: Optional[str]
    started_at: Optional[datetime]
    uptime_seconds: Optional[int]
    current_positions: int = 0

class BotConfigUpdate(BaseModel):
    symbols: Optional[List[str]] = None
    capital: Optional[float] = None
    scan_interval: Optional[int] = None
    max_positions: Optional[int] = None
    risk_per_trade: Optional[float] = None

# Endpoints
@router.post("/start")
async def start_bot(
    config: BotConfig,
    current_user: dict = Depends(get_current_user)
):
    """Inicia el bot del usuario."""
    user_id = str(current_user["id"])

    # Verificar si ya tiene un bot corriendo
    existing = await fetchrow(
        "SELECT id, status FROM bot_instances WHERE user_id = $1 AND status = 'running'",
        user_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot is already running"
        )

    # Verificar límites del plan
    plan = current_user.get("plan_name", "Free")
    limits = await _get_plan_limits(plan)

    if len(config.symbols) > limits["max_symbols"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan {plan} allows max {limits['max_symbols']} symbols"
        )

    if config.capital > limits["max_capital"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan {plan} allows max ${limits['max_capital']} capital"
        )

    if config.mode == "live" and plan == "Free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live mode requires Pro or Enterprise plan"
        )

    # Obtener API keys del usuario
    api_keys = await _get_user_api_keys(user_id, config.mode == "live")
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please configure your API keys first"
        )

    # Crear instancia de bot
    try:
        container_id = await orchestrator.create_bot(
            user_id=user_id,
            config=config.model_dump(),
            api_keys=api_keys,
            mode=config.mode
        )

        # Guardar en DB
        await execute(
            """
            INSERT INTO bot_instances (user_id, container_id, status, mode, config, started_at)
            VALUES ($1, $2, 'running', $3, $4, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                container_id = $2, status = 'running', mode = $3, config = $4, started_at = NOW()
            """,
            user_id, container_id, config.mode, config.model_dump()
        )

        return {
            "message": "Bot started successfully",
            "container_id": container_id[:12],
            "mode": config.mode
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start bot: {str(e)}"
        )

@router.post("/stop")
async def stop_bot(current_user: dict = Depends(get_current_user)):
    """Detiene el bot del usuario."""
    user_id = str(current_user["id"])

    # Obtener instancia actual
    instance = await fetchrow(
        "SELECT container_id FROM bot_instances WHERE user_id = $1 AND status = 'running'",
        user_id
    )

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No bot is currently running"
        )

    # Detener contenedor
    try:
        await orchestrator.stop_bot(user_id)

        # Actualizar DB
        await execute(
            """
            UPDATE bot_instances
            SET status = 'stopped', stopped_at = NOW()
            WHERE user_id = $1
            """,
            user_id
        )

        return {"message": "Bot stopped successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop bot: {str(e)}"
        )

@router.get("/status", response_model=BotStatus)
async def get_bot_status(current_user: dict = Depends(get_current_user)):
    """Obtiene el estado del bot."""
    user_id = str(current_user["id"])

    instance = await fetchrow(
        "SELECT status, mode, started_at, config FROM bot_instances WHERE user_id = $1",
        user_id
    )

    if not instance:
        return BotStatus(status="not_configured")

    # Calcular uptime si está corriendo
    uptime = None
    if instance["status"] == "running" and instance["started_at"]:
        uptime = int((datetime.utcnow() - instance["started_at"]).total_seconds())

    return BotStatus(
        status=instance["status"],
        mode=instance["mode"],
        started_at=instance["started_at"],
        uptime_seconds=uptime
    )

@router.get("/config")
async def get_bot_config(current_user: dict = Depends(get_current_user)):
    """Obtiene la configuración actual del bot."""
    user_id = str(current_user["id"])

    instance = await fetchrow(
        "SELECT config FROM bot_instances WHERE user_id = $1",
        user_id
    )

    if not instance or not instance["config"]:
        # Retornar configuración por defecto
        return BotConfig().model_dump()

    return instance["config"]

@router.put("/config")
async def update_bot_config(
    update: BotConfigUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualiza la configuración del bot (requiere reinicio)."""
    user_id = str(current_user["id"])

    instance = await fetchrow(
        "SELECT config, status FROM bot_instances WHERE user_id = $1",
        user_id
    )

    current_config = instance["config"] if instance else {}

    # Merge configs
    for key, value in update.model_dump(exclude_none=True).items():
        current_config[key] = value

    await execute(
        """
        INSERT INTO bot_instances (user_id, config)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET config = $2
        """,
        user_id, current_config
    )

    needs_restart = instance and instance["status"] == "running"

    return {
        "message": "Configuration updated",
        "needs_restart": needs_restart
    }

@router.post("/restart")
async def restart_bot(current_user: dict = Depends(get_current_user)):
    """Reinicia el bot del usuario."""
    user_id = str(current_user["id"])

    try:
        await orchestrator.restart_bot(user_id)
        return {"message": "Bot restarted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart bot: {str(e)}"
        )

@router.get("/logs")
async def get_bot_logs(
    tail: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Obtiene los últimos logs del bot."""
    user_id = str(current_user["id"])

    logs = await orchestrator.get_logs(user_id, tail=tail)

    return {"logs": logs}

# Helper functions
async def _get_plan_limits(plan_name: str) -> dict:
    """Obtiene los límites de un plan."""
    plan = await fetchrow(
        "SELECT max_symbols, max_capital, features FROM plans WHERE name = $1",
        plan_name
    )

    if not plan:
        # Valores por defecto (Free)
        return {
            "max_symbols": 1,
            "max_capital": 100.0
        }

    return {
        "max_symbols": plan["max_symbols"],
        "max_capital": float(plan["max_capital"])
    }

async def _get_user_api_keys(user_id: str, live_mode: bool) -> dict:
    """Obtiene las API keys del usuario desencriptadas."""
    from core.security import key_encryption

    # Exchange keys
    exchange_row = await fetchrow(
        """
        SELECT api_key_encrypted, api_secret_encrypted
        FROM api_keys
        WHERE user_id = $1 AND exchange = 'binance' AND is_testnet = $2
        """,
        user_id,
        not live_mode  # testnet = not live
    )

    if not exchange_row:
        return None

    # AI keys
    ai_row = await fetchrow(
        """
        SELECT api_key_encrypted, provider
        FROM ai_keys
        WHERE user_id = $1 AND provider = 'deepseek'
        """,
        user_id
    )

    if not ai_row:
        return None

    # Desencriptar
    result = {
        "BINANCE_API_KEY" if live_mode else "BINANCE_TESTNET_API_KEY":
            key_encryption.decrypt(exchange_row["api_key_encrypted"]),
        "BINANCE_API_SECRET" if live_mode else "BINANCE_TESTNET_API_SECRET":
            key_encryption.decrypt(exchange_row["api_secret_encrypted"]),
        "DEEPSEEK_API_KEY": key_encryption.decrypt(ai_row["api_key_encrypted"])
    }

    return result
