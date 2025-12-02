"""
Orchestrator Service - Gestiona contenedores de bots por usuario.
"""

import docker
import os
import yaml
from typing import Optional
import asyncio

from core.config import settings

class BotOrchestrator:
    """Gestiona el ciclo de vida de los bots de trading."""

    def __init__(self):
        self.client = docker.from_env()
        self.network_name = "sath_network"
        self.bot_image = settings.BOT_IMAGE
        self.tenants_path = settings.TENANTS_PATH

    async def create_bot(
        self,
        user_id: str,
        config: dict,
        api_keys: dict,
        mode: str = "paper"
    ) -> str:
        """
        Crea y arranca un contenedor de bot para un usuario.

        Args:
            user_id: ID del usuario
            config: Configuración del bot
            api_keys: API keys desencriptadas
            mode: Modo de operación (paper/live)

        Returns:
            Container ID
        """
        container_name = f"sath_bot_{user_id[:8]}"
        tenant_path = f"{self.tenants_path}/{user_id}"

        # Crear directorios del tenant
        os.makedirs(f"{tenant_path}/config", exist_ok=True)
        os.makedirs(f"{tenant_path}/data", exist_ok=True)
        os.makedirs(f"{tenant_path}/logs", exist_ok=True)

        # Guardar configuración YAML
        await self._save_config(tenant_path, config, mode)

        # Crear archivo .env con keys
        await self._create_env_file(tenant_path, api_keys, user_id)

        # Verificar si ya existe un contenedor con ese nombre
        try:
            existing = self.client.containers.get(container_name)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Variables de entorno base
        environment = {
            "TENANT_ID": user_id,
            "SATH_CONFIG": f"/app/config/config_{mode}.yaml",
            "INFLUXDB_URL": "http://influxdb:8086",
            "INFLUXDB_ORG": "sath_platform",
            "INFLUXDB_BUCKET": f"tenant_{user_id[:8]}",
        }

        # Leer keys del .env y agregar al environment
        env_path = f"{tenant_path}/.env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        environment[key] = value

        # Volúmenes específicos del tenant
        volumes = {
            f"{tenant_path}/config": {"bind": "/app/config", "mode": "ro"},
            f"{tenant_path}/data": {"bind": "/app/data", "mode": "rw"},
            f"{tenant_path}/logs": {"bind": "/app/logs", "mode": "rw"},
        }

        # Crear y arrancar contenedor
        container = self.client.containers.run(
            self.bot_image,
            name=container_name,
            environment=environment,
            volumes=volumes,
            network=self.network_name,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            mem_limit="1g",
            cpu_quota=100000,  # 1 CPU
            labels={
                "sath.tenant_id": user_id,
                "sath.type": "bot",
                "sath.mode": mode
            }
        )

        return container.id

    async def stop_bot(self, user_id: str) -> bool:
        """Detiene el bot de un usuario."""
        container_name = f"sath_bot_{user_id[:8]}"
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=60)  # Grace period
            container.remove()
            return True
        except docker.errors.NotFound:
            return False

    async def restart_bot(self, user_id: str) -> bool:
        """Reinicia el bot de un usuario."""
        container_name = f"sath_bot_{user_id[:8]}"
        try:
            container = self.client.containers.get(container_name)
            container.restart(timeout=60)
            return True
        except docker.errors.NotFound:
            return False

    async def get_status(self, user_id: str) -> dict:
        """Obtiene el estado del bot de un usuario."""
        container_name = f"sath_bot_{user_id[:8]}"
        try:
            container = self.client.containers.get(container_name)
            return {
                "status": container.status,
                "started_at": container.attrs["State"]["StartedAt"],
                "health": container.attrs.get("State", {}).get("Health", {}).get("Status")
            }
        except docker.errors.NotFound:
            return {"status": "not_found"}

    async def get_logs(self, user_id: str, tail: int = 100) -> str:
        """Obtiene los últimos logs del bot."""
        container_name = f"sath_bot_{user_id[:8]}"

        # Primero intentar del contenedor
        try:
            container = self.client.containers.get(container_name)
            return container.logs(tail=tail).decode("utf-8")
        except docker.errors.NotFound:
            pass

        # Si no hay contenedor, leer del archivo
        log_path = f"{self.tenants_path}/{user_id}/logs/trading_bot.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                lines = f.readlines()
                return "".join(lines[-tail:])

        return ""

    async def _save_config(self, tenant_path: str, config: dict, mode: str):
        """Guarda la configuración del bot en YAML."""
        # Convertir config del frontend a formato YAML del bot
        bot_config = {
            "mode": mode,
            "trading": {
                "symbols": config.get("symbols", ["BTC/USDT"]),
                "scan_interval_seconds": config.get("scan_interval", 180),
                "max_positions_per_symbol": config.get("max_positions", 1),
            },
            "risk": {
                "initial_capital": config.get("capital", 100.0),
                "risk_per_trade": config.get("risk_per_trade", 0.02),
                "max_drawdown_percent": 15.0,
            },
            "ai": {
                "provider": "deepseek",
                "fast_model": "deepseek-chat",
                "deep_model": "deepseek-reasoner",
            }
        }

        config_path = f"{tenant_path}/config/config_{mode}.yaml"
        with open(config_path, "w") as f:
            yaml.dump(bot_config, f, default_flow_style=False)

    async def _create_env_file(self, tenant_path: str, api_keys: dict, user_id: str):
        """Crea archivo .env con las API keys."""
        env_lines = []
        for key, value in api_keys.items():
            env_lines.append(f"{key}={value}")

        # Agregar variables adicionales
        env_lines.append(f"TENANT_ID={user_id}")

        env_path = f"{tenant_path}/.env"
        with open(env_path, "w") as f:
            f.write("\n".join(env_lines))

        # Permisos restrictivos
        os.chmod(env_path, 0o600)

    def list_all_bots(self) -> list:
        """Lista todos los bots corriendo (para admin)."""
        containers = self.client.containers.list(
            filters={"label": "sath.type=bot"}
        )

        return [
            {
                "container_id": c.id[:12],
                "name": c.name,
                "status": c.status,
                "tenant_id": c.labels.get("sath.tenant_id"),
                "mode": c.labels.get("sath.mode")
            }
            for c in containers
        ]

    def get_stats(self) -> dict:
        """Obtiene estadísticas globales de bots."""
        containers = self.client.containers.list(
            filters={"label": "sath.type=bot"}
        )

        running = sum(1 for c in containers if c.status == "running")

        return {
            "total_bots": len(containers),
            "running": running,
            "stopped": len(containers) - running
        }
