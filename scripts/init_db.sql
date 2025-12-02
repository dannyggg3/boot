-- ============================================
-- SATH Platform - Database Schema
-- ============================================

-- Extension para UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(20) DEFAULT 'user'
);

-- Tabla de planes
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    price_monthly DECIMAL(10,2) DEFAULT 0,
    price_yearly DECIMAL(10,2) DEFAULT 0,
    max_symbols INTEGER DEFAULT 1,
    max_capital DECIMAL(15,2) DEFAULT 100,
    features JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de suscripciones
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES plans(id),
    status VARCHAR(20) DEFAULT 'active',
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    stripe_subscription_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de instancias de bot
CREATE TABLE IF NOT EXISTS bot_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    container_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'stopped',
    mode VARCHAR(20) DEFAULT 'paper',
    config JSONB,
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    stopped_at TIMESTAMP
);

-- Tabla de API keys de exchanges (encriptadas)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    api_key_encrypted BYTEA NOT NULL,
    api_secret_encrypted BYTEA NOT NULL,
    is_testnet BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, exchange, is_testnet)
);

-- Tabla de API keys de IA (encriptadas)
CREATE TABLE IF NOT EXISTS ai_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    api_key_encrypted BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Insertar planes por defecto
INSERT INTO plans (name, price_monthly, price_yearly, max_symbols, max_capital, features) VALUES
    ('Free', 0, 0, 1, 100, '{"paper_only": true, "mtf_analysis": false, "ai_ensemble": false}'),
    ('Pro', 29, 290, 5, 10000, '{"paper_only": false, "mtf_analysis": true, "ai_ensemble": false}'),
    ('Enterprise', 99, 990, 100, 1000000, '{"paper_only": false, "mtf_analysis": true, "ai_ensemble": true}')
ON CONFLICT (name) DO NOTHING;

-- Índices
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_instances_user ON bot_instances(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_keys_user ON ai_keys(user_id);

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para users
DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
