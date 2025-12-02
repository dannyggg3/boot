# SATH Multi-Tenant SaaS Architecture

## Resumen Ejecutivo

Transformación del bot single-tenant a una plataforma SaaS multi-tenant donde cada usuario tiene:
- Su propia instancia aislada
- Sus propias API keys (Binance, DeepSeek, etc.)
- Sus propios logs y datos
- Su propia configuración
- Facturación independiente

---

## Modelo de Arquitectura: Container-per-Tenant

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOAD BALANCER                                   │
│                         (Nginx / Traefik / CloudFlare)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
         ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
         │   WEB DASHBOARD  │ │  API GATEWAY │ │  ADMIN PANEL     │
         │   (Next.js/React)│ │  (FastAPI)   │ │  (Internal)      │
         │   Puerto: 3000   │ │  Puerto: 8000│ │  Puerto: 8001    │
         └──────────────────┘ └──────────────┘ └──────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
         ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
         │   PostgreSQL     │ │    Redis     │ │   InfluxDB       │
         │   (Usuarios,     │ │  (Cache,     │ │   (Métricas      │
         │    Billing,      │ │   Sessions,  │ │    globales)     │
         │    Plans)        │ │   Queue)     │ │                  │
         └──────────────────┘ └──────────────┘ └──────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR SERVICE                               │
│                     (Gestiona ciclo de vida de bots)                        │
│                                                                              │
│  • Crear/Destruir contenedores por usuario                                  │
│  • Health checks de instancias                                              │
│  • Auto-scaling                                                             │
│  • Logs aggregation                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│  TENANT: user_1 │        │  TENANT: user_2 │        │  TENANT: user_N │
│  ┌───────────┐  │        │  ┌───────────┐  │        │  ┌───────────┐  │
│  │ SATH Bot  │  │        │  │ SATH Bot  │  │        │  │ SATH Bot  │  │
│  │ Container │  │        │  │ Container │  │        │  │ Container │  │
│  └───────────┘  │        └───────────┘  │        │  └───────────┘  │
│  ┌───────────┐  │        │  ┌───────────┐  │        │  ┌───────────┐  │
│  │  Config   │  │        │  │  Config   │  │        │  │  Config   │  │
│  │  Logs     │  │        │  │  Logs     │  │        │  │  Logs     │  │
│  │  Data     │  │        │  │  Data     │  │        │  │  Data     │  │
│  └───────────┘  │        │  └───────────┘  │        │  └───────────┘  │
└─────────────────┘        └─────────────────┘        └─────────────────┘
```

---

## Estructura de Directorios Nueva

```
sath-platform/
├── docker-compose.yml              # Servicios core (DB, Redis, API)
├── docker-compose.override.yml     # Desarrollo local
│
├── api/                            # API Gateway (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Login, registro, JWT
│   │   ├── users.py                # CRUD usuarios
│   │   ├── bots.py                 # Start/Stop/Config bots
│   │   ├── billing.py              # Planes, pagos, suscripciones
│   │   └── webhooks.py             # Stripe, Telegram callbacks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Docker API para gestionar bots
│   │   ├── encryption.py           # Cifrado de API keys
│   │   └── billing_service.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── subscription.py
│   │   └── bot_instance.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user_schemas.py
│   │   └── bot_schemas.py
│   └── core/
│       ├── config.py
│       ├── security.py
│       └── database.py
│
├── bot/                            # Bot de Trading (código actual)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── src/
│   │   ├── engines/
│   │   ├── modules/
│   │   ├── schemas/
│   │   └── utils/
│   └── entrypoint.sh               # Script de inicio con tenant_id
│
├── dashboard/                      # Frontend Web (Next.js)
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/
│   │   │   ├── dashboard/
│   │   │   ├── settings/
│   │   │   ├── billing/
│   │   │   └── logs/
│   │   ├── components/
│   │   └── lib/
│   └── public/
│
├── orchestrator/                   # Servicio de orquestación
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── docker_manager.py           # Crear/destruir contenedores
│   ├── health_checker.py           # Monitoreo de instancias
│   └── log_aggregator.py           # Centralizar logs
│
├── tenants/                        # Datos por usuario (VOLUME)
│   └── {user_id}/
│       ├── config/
│       │   └── config.yaml
│       ├── data/
│       │   ├── positions.db
│       │   └── metrics.json
│       ├── logs/
│       │   └── trading_bot.log
│       └── .env                    # Keys encriptadas
│
├── shared/                         # Código compartido
│   ├── encryption/
│   │   └── key_manager.py
│   └── schemas/
│       └── events.py
│
├── nginx/                          # Reverse Proxy
│   ├── nginx.conf
│   └── ssl/
│
├── scripts/
│   ├── init_db.py
│   ├── create_tenant.py
│   ├── migrate.py
│   └── backup.py
│
├── .env.example
├── .env
└── README.md
```

---

## Base de Datos Central (PostgreSQL)

### Tabla: users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(20) DEFAULT 'user'  -- user, admin, superadmin
);
```

### Tabla: subscriptions
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan_id UUID REFERENCES plans(id),
    status VARCHAR(20) DEFAULT 'active',  -- active, cancelled, expired, trial
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    stripe_subscription_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabla: plans
```sql
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,           -- Free, Pro, Enterprise
    price_monthly DECIMAL(10,2),
    price_yearly DECIMAL(10,2),
    max_symbols INTEGER DEFAULT 3,        -- Símbolos simultáneos
    max_capital DECIMAL(15,2),            -- Capital máximo
    features JSONB,                       -- Features habilitadas
    is_active BOOLEAN DEFAULT TRUE
);
```

### Tabla: bot_instances
```sql
CREATE TABLE bot_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    container_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'stopped',  -- running, stopped, error, starting
    mode VARCHAR(20) DEFAULT 'paper',      -- paper, live
    config JSONB,                          -- Configuración del bot
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    stopped_at TIMESTAMP
);
```

### Tabla: api_keys (ENCRIPTADAS)
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    exchange VARCHAR(50) NOT NULL,         -- binance, binance_testnet
    api_key_encrypted BYTEA NOT NULL,      -- Encriptado con AES-256
    api_secret_encrypted BYTEA NOT NULL,
    is_testnet BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, exchange, is_testnet)
);
```

### Tabla: ai_keys (ENCRIPTADAS)
```sql
CREATE TABLE ai_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,         -- deepseek, openai, gemini
    api_key_encrypted BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider)
);
```

---

## API Endpoints

### Autenticación
```
POST   /api/v1/auth/register          # Registro
POST   /api/v1/auth/login              # Login → JWT
POST   /api/v1/auth/refresh            # Refresh token
POST   /api/v1/auth/logout             # Logout
POST   /api/v1/auth/forgot-password    # Recuperar contraseña
POST   /api/v1/auth/verify-email       # Verificar email
```

### Usuario
```
GET    /api/v1/users/me                # Perfil actual
PUT    /api/v1/users/me                # Actualizar perfil
DELETE /api/v1/users/me                # Eliminar cuenta
```

### API Keys
```
POST   /api/v1/keys/exchange           # Guardar keys de exchange
GET    /api/v1/keys/exchange           # Listar exchanges configurados
DELETE /api/v1/keys/exchange/{id}      # Eliminar key
POST   /api/v1/keys/ai                 # Guardar key de IA
GET    /api/v1/keys/ai                 # Listar proveedores configurados
POST   /api/v1/keys/test               # Probar conexión
```

### Bot Control
```
POST   /api/v1/bot/start               # Iniciar bot
POST   /api/v1/bot/stop                # Detener bot
GET    /api/v1/bot/status              # Estado del bot
PUT    /api/v1/bot/config              # Actualizar configuración
GET    /api/v1/bot/config              # Obtener configuración
POST   /api/v1/bot/restart             # Reiniciar bot
```

### Logs & Métricas
```
GET    /api/v1/logs                    # Obtener logs (paginado)
GET    /api/v1/logs/stream             # WebSocket para logs en tiempo real
GET    /api/v1/metrics                 # Métricas de rendimiento
GET    /api/v1/positions               # Posiciones abiertas
GET    /api/v1/trades                  # Historial de trades
```

### Billing
```
GET    /api/v1/billing/plans           # Listar planes
POST   /api/v1/billing/subscribe       # Suscribirse a plan
POST   /api/v1/billing/cancel          # Cancelar suscripción
GET    /api/v1/billing/invoices        # Historial de facturas
POST   /api/v1/billing/webhook/stripe  # Webhook de Stripe
```

### Admin (solo admins)
```
GET    /api/v1/admin/users             # Listar usuarios
GET    /api/v1/admin/bots              # Listar todos los bots
POST   /api/v1/admin/bots/{id}/stop    # Forzar stop de bot
GET    /api/v1/admin/stats             # Estadísticas globales
```

---

## Docker Compose Principal

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Base de datos principal
  postgres:
    image: postgres:15
    container_name: sath_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: sath_platform
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - sath_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Cache y Queue
  redis:
    image: redis:7-alpine
    container_name: sath_redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - sath_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Métricas globales
  influxdb:
    image: influxdb:2.7
    container_name: sath_influxdb
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: ${INFLUXDB_USER}
      DOCKER_INFLUXDB_INIT_PASSWORD: ${INFLUXDB_PASSWORD}
      DOCKER_INFLUXDB_INIT_ORG: sath_platform
      DOCKER_INFLUXDB_INIT_BUCKET: global_metrics
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${INFLUXDB_TOKEN}
    volumes:
      - influxdb_data:/var/lib/influxdb2
    networks:
      - sath_network

  # API Gateway
  api:
    build: ./api
    container_name: sath_api
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/sath_platform
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Para controlar Docker
      - ./tenants:/app/tenants
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - sath_network
    ports:
      - "8000:8000"

  # Web Dashboard
  dashboard:
    build: ./dashboard
    container_name: sath_dashboard
    environment:
      NEXT_PUBLIC_API_URL: ${API_URL}
    networks:
      - sath_network
    ports:
      - "3000:3000"

  # Orchestrator (gestión de bots)
  orchestrator:
    build: ./orchestrator
    container_name: sath_orchestrator
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/sath_platform
      REDIS_URL: redis://redis:6379
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./tenants:/app/tenants
      - ./bot:/app/bot  # Para construir imágenes
    depends_on:
      - postgres
      - redis
    networks:
      - sath_network

  # Grafana (métricas globales)
  grafana:
    image: grafana/grafana:latest
    container_name: sath_grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - sath_network
    ports:
      - "3001:3000"

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: sath_nginx
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
      - dashboard
    networks:
      - sath_network

networks:
  sath_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  influxdb_data:
  grafana_data:
```

---

## Orchestrator: Crear Bot por Usuario

```python
# orchestrator/docker_manager.py
import docker
import os
from typing import Optional
import uuid

class BotManager:
    def __init__(self):
        self.client = docker.from_env()
        self.network_name = "sath_network"
        self.bot_image = "sath-bot:latest"
        self.tenants_path = "/app/tenants"

    def create_bot_instance(
        self,
        user_id: str,
        config: dict,
        api_keys: dict,
        mode: str = "paper"
    ) -> str:
        """Crea un contenedor de bot para un usuario."""

        container_name = f"sath_bot_{user_id[:8]}"
        tenant_path = f"{self.tenants_path}/{user_id}"

        # Crear directorios del tenant
        os.makedirs(f"{tenant_path}/config", exist_ok=True)
        os.makedirs(f"{tenant_path}/data", exist_ok=True)
        os.makedirs(f"{tenant_path}/logs", exist_ok=True)

        # Guardar configuración
        self._save_config(tenant_path, config, mode)

        # Crear .env con keys desencriptadas
        self._create_env_file(tenant_path, api_keys)

        # Variables de entorno para el contenedor
        environment = {
            "TENANT_ID": user_id,
            "SATH_CONFIG": f"/app/tenant/config/config_{mode}.yaml",
            "INFLUXDB_URL": "http://influxdb:8086",
            "INFLUXDB_ORG": "sath_platform",
            "INFLUXDB_BUCKET": f"tenant_{user_id[:8]}",
        }

        # Leer keys del .env
        env_file = f"{tenant_path}/.env"

        # Volúmenes específicos del tenant
        volumes = {
            f"{tenant_path}/config": {"bind": "/app/config", "mode": "ro"},
            f"{tenant_path}/data": {"bind": "/app/data", "mode": "rw"},
            f"{tenant_path}/logs": {"bind": "/app/logs", "mode": "rw"},
        }

        # Crear contenedor
        container = self.client.containers.run(
            self.bot_image,
            name=container_name,
            environment=environment,
            env_file=env_file,
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

    def stop_bot_instance(self, user_id: str) -> bool:
        """Detiene el bot de un usuario."""
        container_name = f"sath_bot_{user_id[:8]}"
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=60)  # Grace period para cerrar posiciones
            container.remove()
            return True
        except docker.errors.NotFound:
            return False

    def get_bot_status(self, user_id: str) -> dict:
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

    def get_bot_logs(self, user_id: str, tail: int = 100) -> str:
        """Obtiene los últimos logs del bot."""
        container_name = f"sath_bot_{user_id[:8]}"
        try:
            container = self.client.containers.get(container_name)
            return container.logs(tail=tail).decode("utf-8")
        except docker.errors.NotFound:
            # Leer del archivo de logs
            log_path = f"{self.tenants_path}/{user_id}/logs/trading_bot.log"
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    lines = f.readlines()
                    return "".join(lines[-tail:])
            return ""

    def restart_bot_instance(self, user_id: str) -> bool:
        """Reinicia el bot de un usuario."""
        container_name = f"sath_bot_{user_id[:8]}"
        try:
            container = self.client.containers.get(container_name)
            container.restart(timeout=60)
            return True
        except docker.errors.NotFound:
            return False

    def _save_config(self, tenant_path: str, config: dict, mode: str):
        """Guarda la configuración del bot."""
        import yaml
        config_path = f"{tenant_path}/config/config_{mode}.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

    def _create_env_file(self, tenant_path: str, api_keys: dict):
        """Crea archivo .env con las API keys."""
        env_content = []
        for key, value in api_keys.items():
            env_content.append(f"{key}={value}")

        env_path = f"{tenant_path}/.env"
        with open(env_path, "w") as f:
            f.write("\n".join(env_content))

        # Permisos restrictivos
        os.chmod(env_path, 0o600)
```

---

## Seguridad: Encriptación de API Keys

```python
# api/services/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class KeyEncryption:
    def __init__(self, master_key: str):
        """
        Inicializa el encriptador con una master key.
        La master key debe estar en una variable de entorno segura.
        """
        # Derivar key de encriptación de la master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'sath_platform_salt_v1',  # En producción: salt único por instalación
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encripta un texto plano."""
        return self.fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Desencripta un texto cifrado."""
        return self.fernet.decrypt(ciphertext).decode()


# Uso en el API
class APIKeyService:
    def __init__(self, db, encryption: KeyEncryption):
        self.db = db
        self.encryption = encryption

    async def save_exchange_keys(
        self,
        user_id: str,
        exchange: str,
        api_key: str,
        api_secret: str,
        is_testnet: bool = False
    ):
        """Guarda las API keys encriptadas."""
        encrypted_key = self.encryption.encrypt(api_key)
        encrypted_secret = self.encryption.encrypt(api_secret)

        # Guardar en DB
        await self.db.execute(
            """
            INSERT INTO api_keys (user_id, exchange, api_key_encrypted, api_secret_encrypted, is_testnet)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, exchange, is_testnet)
            DO UPDATE SET api_key_encrypted = $3, api_secret_encrypted = $4
            """,
            user_id, exchange, encrypted_key, encrypted_secret, is_testnet
        )

    async def get_exchange_keys(
        self,
        user_id: str,
        exchange: str,
        is_testnet: bool = False
    ) -> dict:
        """Obtiene las API keys desencriptadas."""
        row = await self.db.fetchrow(
            """
            SELECT api_key_encrypted, api_secret_encrypted
            FROM api_keys
            WHERE user_id = $1 AND exchange = $2 AND is_testnet = $3
            """,
            user_id, exchange, is_testnet
        )

        if not row:
            return None

        return {
            "api_key": self.encryption.decrypt(row["api_key_encrypted"]),
            "api_secret": self.encryption.decrypt(row["api_secret_encrypted"])
        }
```

---

## Planes y Límites

| Feature | Free | Pro ($29/mes) | Enterprise ($99/mes) |
|---------|------|---------------|---------------------|
| Símbolos | 1 | 5 | Ilimitado |
| Capital máximo | $100 | $10,000 | Ilimitado |
| Modo | Paper only | Paper + Live | Paper + Live |
| Análisis MTF | No | Sí | Sí |
| AI Ensemble | No | No | Sí |
| Soporte | Community | Email | Prioritario |
| API Access | No | No | Sí |
| Logs retention | 7 días | 30 días | 90 días |

---

## Flujo de Usuario

```
1. REGISTRO
   └─→ Verificar email
       └─→ Plan Free automático

2. CONFIGURACIÓN
   └─→ Ingresar API Keys (Binance Testnet)
       └─→ Ingresar API Key (DeepSeek)
           └─→ Configurar símbolos y capital

3. INICIAR BOT
   └─→ API crea contenedor Docker
       └─→ Bot inicia con configuración del usuario
           └─→ Dashboard muestra logs en tiempo real

4. UPGRADE A PRO
   └─→ Stripe checkout
       └─→ Webhook actualiza plan
           └─→ Límites aumentados
               └─→ Puede agregar más símbolos
                   └─→ Puede usar modo LIVE

5. BOT RUNNING
   └─→ Monitoreo de salud cada 60s
       └─→ Logs centralizados
           └─→ Métricas en Grafana
               └─→ Notificaciones Telegram
```

---

## Próximos Pasos de Implementación

### Fase 1: Backend Core (2-3 semanas)
- [ ] Setup PostgreSQL + Redis
- [ ] API FastAPI con autenticación JWT
- [ ] Modelo de usuarios y suscripciones
- [ ] Encriptación de API keys
- [ ] Orchestrator básico (crear/destruir bots)

### Fase 2: Dashboard (2 semanas)
- [ ] Login/Registro con Next.js
- [ ] Configuración de API keys
- [ ] Panel de control del bot
- [ ] Visualización de logs
- [ ] Configuración de parámetros

### Fase 3: Billing (1 semana)
- [ ] Integración con Stripe
- [ ] Planes y límites
- [ ] Webhooks de pago
- [ ] Portal de facturación

### Fase 4: Production Ready (1-2 semanas)
- [ ] SSL/TLS con Let's Encrypt
- [ ] Backups automáticos
- [ ] Monitoreo con Prometheus/Grafana
- [ ] Rate limiting
- [ ] Logs centralizados (Loki)

---

## Consideraciones de Seguridad

1. **API Keys**: Encriptadas en reposo con AES-256
2. **Passwords**: Hasheados con bcrypt (cost factor 12)
3. **JWT**: Tokens de corta duración (15 min) + refresh tokens
4. **HTTPS**: Obligatorio en producción
5. **Rate Limiting**: Por usuario y por IP
6. **Aislamiento**: Cada bot en su propio contenedor
7. **Docker Socket**: Solo accesible por orchestrator
8. **Secrets**: Variables de entorno, nunca en código
9. **Backups**: Encriptados y en ubicación separada

---

## Estimación de Recursos por Usuario

| Recurso | Por Bot |
|---------|---------|
| RAM | ~500MB |
| CPU | ~0.25 cores |
| Disco | ~100MB logs/mes |
| Network | ~1GB/mes |

**Servidor recomendado para 50 usuarios activos:**
- 32GB RAM
- 8 vCPU
- 200GB SSD
- ~$150-200/mes en cloud
