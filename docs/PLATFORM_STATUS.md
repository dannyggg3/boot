# SATH Platform - Estado Actual

## Resumen

Se ha implementado una arquitectura multi-tenant para convertir el bot de trading en una plataforma SaaS.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    SATH PLATFORM                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  PostgreSQL │  │    Redis    │  │      InfluxDB       │ │
│  │   :5432     │  │   :6379     │  │       :8086         │ │
│  │  (usuarios, │  │  (cache,    │  │  (métricas de       │ │
│  │   billing)  │  │   sesiones) │  │   todos los bots)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Platform API (:8080)                    │   │
│  │  FastAPI - Gestión de usuarios, bots, billing        │   │
│  │  /api/v1/auth/* - Autenticación JWT                  │   │
│  │  /api/v1/users/* - Gestión de usuarios               │   │
│  │  /api/v1/bot/* - Control de bots                     │   │
│  │  /api/v1/keys/* - API Keys (encriptadas)             │   │
│  │  /api/v1/billing/* - Suscripciones (Stripe)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────┐                                           │
│  │   Grafana   │                                           │
│  │   :3002     │                                           │
│  └─────────────┘                                           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    BOTS POR USUARIO                         │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ bot_user_abc  │  │ bot_user_def  │  │ bot_user_xyz  │   │
│  │ (container)   │  │ (container)   │  │ (container)   │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Servicios Desplegados

### Platform (Multi-tenant)

| Servicio | Container | Puerto | Estado |
|----------|-----------|--------|--------|
| PostgreSQL | platform_postgres | 5432 | ✅ Running |
| Redis | platform_redis | 6379 | ✅ Running |
| InfluxDB | platform_influxdb | 8086 | ✅ Running |
| API | platform_api | 8080 | ⚠️ Pendiente fix bcrypt |
| Grafana | platform_grafana | 3002 | ✅ Running |

### Bot Individual (Paper Trading)

| Servicio | Container | Puerto | Estado |
|----------|-----------|--------|--------|
| InfluxDB | sath_influxdb_paper | 8087 | ✅ Running |
| Bot | sath_bot_paper | - | ✅ Running |
| Grafana | sath_grafana_paper | 3001 | ✅ Running |

---

## Archivos de Configuración

### Docker Compose Files

| Archivo | Propósito |
|---------|-----------|
| `docker-compose.platform.yml` | Servicios centrales de la plataforma |
| `docker-compose.paper.yml` | Bot individual modo paper/testnet |
| `docker-compose.live.yml` | Bot individual modo live/producción |
| `docker-compose.bot-only.yml` | Template para bots de usuarios (orquestador) |

### Environment Files

| Archivo | Propósito | Git |
|---------|-----------|-----|
| `.env` | Variables del bot individual | ❌ Ignorado |
| `.env.platform` | Variables de la plataforma | ❌ Ignorado |

---

## API Endpoints

### Autenticación (`/api/v1/auth/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/register` | Registrar nuevo usuario |
| POST | `/login` | Iniciar sesión (JWT) |
| POST | `/refresh` | Renovar access token |
| POST | `/logout` | Cerrar sesión |

### Usuarios (`/api/v1/users/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/me` | Obtener perfil |
| PUT | `/me` | Actualizar perfil |
| DELETE | `/me` | Desactivar cuenta |

### Bot (`/api/v1/bot/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/start` | Iniciar bot |
| POST | `/stop` | Detener bot |
| GET | `/status` | Estado del bot |
| GET | `/config` | Obtener configuración |
| PUT | `/config` | Actualizar configuración |
| POST | `/restart` | Reiniciar bot |
| GET | `/logs` | Obtener logs |

### API Keys (`/api/v1/keys/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/exchange` | Guardar keys de exchange |
| GET | `/exchange` | Listar exchanges configurados |
| DELETE | `/exchange/{id}` | Eliminar key |
| POST | `/ai` | Guardar key de IA |
| GET | `/ai` | Listar proveedores IA |
| DELETE | `/ai/{id}` | Eliminar key IA |
| POST | `/test` | Probar conexión |

### Billing (`/api/v1/billing/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/plans` | Listar planes |
| GET | `/subscription` | Suscripción actual |
| POST | `/subscribe` | Suscribirse a plan |
| POST | `/cancel` | Cancelar suscripción |
| GET | `/invoices` | Historial de facturas |

---

## Estructura de Archivos API

```
api/
├── Dockerfile
├── requirements.txt
├── main.py              # Entry point FastAPI
├── config.py            # Settings con Pydantic
├── database.py          # Conexión PostgreSQL async
├── models/
│   └── schemas.py       # Pydantic models
├── routers/
│   ├── __init__.py
│   ├── auth.py          # Autenticación JWT
│   ├── users.py         # Gestión usuarios
│   ├── bots.py          # Control de bots
│   ├── keys.py          # API keys encriptadas
│   └── billing.py       # Suscripciones Stripe
└── services/
    ├── auth_service.py  # Lógica de auth
    ├── encryption.py    # AES-256 para keys
    └── orchestrator.py  # Docker container mgmt
```

---

## Base de Datos (PostgreSQL)

### Tablas

```sql
-- Usuarios
users (id, email, password_hash, name, is_active, plan, created_at)

-- Planes de suscripción
plans (id, name, price_monthly, price_yearly, max_symbols, max_capital, features)

-- Suscripciones activas
subscriptions (id, user_id, plan_id, status, stripe_subscription_id, started_at, expires_at)

-- Instancias de bots
bot_instances (id, user_id, container_id, status, mode, config, started_at)

-- API Keys de exchanges (encriptadas)
api_keys (id, user_id, exchange, encrypted_key, encrypted_secret, is_testnet, created_at)

-- API Keys de IA (encriptadas)
ai_keys (id, user_id, provider, encrypted_key, created_at)
```

---

## Seguridad

- **JWT**: Access tokens (15min) + Refresh tokens (7 días)
- **Passwords**: Bcrypt hash con passlib
- **API Keys**: Encriptación AES-256 (Fernet) en reposo
- **Docker Socket**: Acceso controlado para orquestador

---

## Comandos de Operación

### Levantar Platform
```bash
docker compose -p platform -f docker-compose.platform.yml --env-file .env.platform up -d
```

### Levantar Bot Paper
```bash
docker compose -p paper -f docker-compose.paper.yml --env-file .env up -d
```

### Ver logs
```bash
docker logs platform_api --tail 50
docker logs sath_bot_paper --tail 50
```

### Rebuild API
```bash
docker compose -p platform -f docker-compose.platform.yml --env-file .env.platform build --no-cache api
docker compose -p platform -f docker-compose.platform.yml --env-file .env.platform up -d api
```

---

## Pendientes

### Inmediatos
- [ ] Fix bcrypt compatibility en API (pin bcrypt==4.0.1)
- [ ] Probar registro de usuarios
- [ ] Probar login y JWT

### Próximos
- [ ] Configurar Stripe para billing real
- [ ] Frontend/Dashboard para usuarios
- [ ] Sistema de notificaciones
- [ ] Métricas por usuario en InfluxDB
- [ ] Rate limiting en API
- [ ] Logs centralizados

---

## URLs de Acceso (Servidor: 51.161.8.217)

| Servicio | URL |
|----------|-----|
| Platform API Docs | http://51.161.8.217:8080/docs |
| Platform Grafana | http://51.161.8.217:3002 |
| Paper Grafana | http://51.161.8.217:3001 |
| InfluxDB Platform | http://51.161.8.217:8086 |

---

## Fixes Aplicados en Esta Sesión

1. **KeyError 'samples'** - `institutional_metrics.py`
   - Agregado `'samples': 0` a retornos vacíos
   - Cambiado acceso directo a `.get('samples', 0)`

2. **Docker volumes para dev** - Todos los compose
   - Agregado `./src:/app/src` y `./main.py:/app/main.py`

3. **Puerto Grafana conflicto** - `docker-compose.platform.yml`
   - Platform Grafana movido de 3001 a 3002

4. **email-validator** - `api/requirements.txt`
   - Cambiado `pydantic` a `pydantic[email]`

5. **Docker requests incompatibility** - `api/requirements.txt`
   - Agregado `requests<2.32.0`

6. **Docker socket permissions** - `api/Dockerfile`
   - Removido usuario no-root para acceso a docker.sock

7. **bcrypt/passlib** - `api/requirements.txt` (pendiente deploy)
   - Agregado `bcrypt==4.0.1`
