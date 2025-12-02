# Diccionario Completo de Trading - SATH Bot

> **Guía educativa completa** para entender trading algorítmico desde cero.
> Documento creado para el proyecto SATH (Smart Adaptive Trading Helper) v1.7+

---

## Tabla de Contenidos

1. [Conceptos Básicos de Trading](#1-conceptos-básicos-de-trading)
2. [Tipos de Mercados](#2-tipos-de-mercados)
3. [Tipos de Órdenes](#3-tipos-de-órdenes)
4. [Posiciones y Direcciones](#4-posiciones-y-direcciones)
5. [Gestión de Riesgo](#5-gestión-de-riesgo)
6. [Análisis Técnico](#6-análisis-técnico)
7. [Indicadores Técnicos](#7-indicadores-técnicos)
8. [Patrones de Velas (Candlesticks)](#8-patrones-de-velas-candlesticks)
9. [Timeframes (Marcos Temporales)](#9-timeframes-marcos-temporales)
10. [Conceptos de Criptomonedas](#10-conceptos-de-criptomonedas)
11. [Trading Algorítmico](#11-trading-algorítmico)
12. [Términos Específicos de SATH](#12-términos-específicos-de-sath)
13. [Fórmulas Importantes](#13-fórmulas-importantes)
14. [Ejemplos Prácticos](#14-ejemplos-prácticos)

---

## 1. Conceptos Básicos de Trading

### ¿Qué es Trading?

**Trading** es la actividad de comprar y vender activos financieros (acciones, criptomonedas, divisas, etc.) con el objetivo de obtener ganancias aprovechando las fluctuaciones de precios.

```
Ejemplo Simple:
- Compras Bitcoin a $30,000
- El precio sube a $35,000
- Vendes y ganas $5,000 (menos comisiones)
```

### Términos Fundamentales

| Término | Definición | Ejemplo |
|---------|------------|---------|
| **Activo** | Cualquier cosa que puedas comprar/vender | Bitcoin, Ethereum, acciones de Apple |
| **Par de Trading** | Dos activos que se intercambian | BTC/USDT = Bitcoin contra Tether |
| **Precio** | Valor actual de un activo | SOL = $139.70 |
| **Volumen** | Cantidad de activo negociado en un período | 1,000,000 SOL en 24h |
| **Liquidez** | Facilidad para comprar/vender sin afectar el precio | Alta liquidez = mejor para trading |
| **Spread** | Diferencia entre precio de compra y venta | Compra: $100.05, Venta: $100.00, Spread: $0.05 |
| **Ticker/Symbol** | Código que identifica un activo | BTC, ETH, SOL |

### El Libro de Órdenes (Order Book)

```
         VENDEDORES (Asks/Offers)
         ┌─────────────────────┐
         │ $100.05  -  50 BTC  │  ← Precio más bajo al que alguien vende
         │ $100.10  -  30 BTC  │
         │ $100.15  -  100 BTC │
         ├─────────────────────┤
         │    SPREAD: $0.05    │
         ├─────────────────────┤
         │ $100.00  -  75 BTC  │  ← Precio más alto al que alguien compra
         │ $99.95   -  40 BTC  │
         │ $99.90   -  120 BTC │
         └─────────────────────┘
         COMPRADORES (Bids)
```

---

## 2. Tipos de Mercados

### Mercado Spot

**Definición:** Compras el activo real y lo posees.

```
Ejemplo:
- Tienes $1,000 USDT
- Compras 10 SOL a $100 cada uno
- Ahora tienes 10 SOL reales en tu wallet
- Si SOL sube a $150, tus 10 SOL valen $1,500
- Ganancia: $500 (50%)
```

**Características:**
- Solo puedes ganar si el precio SUBE
- No hay riesgo de liquidación
- Máxima pérdida: lo que invertiste

### Mercado de Futuros (Futures)

**Definición:** Contratos que te permiten especular sobre el precio futuro sin poseer el activo.

```
Ejemplo:
- Tienes $100 USDT como margen
- Abres un contrato de futuros de SOL con 10x de apalancamiento
- Controlas $1,000 en valor de SOL
- Si SOL sube 10%, ganas $100 (100% de tu margen)
- Si SOL baja 10%, pierdes $100 (100% de tu margen = LIQUIDACIÓN)
```

**Características:**
- Puedes ganar si el precio sube (LONG) o baja (SHORT)
- Usas apalancamiento (multiplicador)
- Riesgo de liquidación si el precio va muy en contra

### Futuros Perpetuos (Perpetual Futures)

**Definición:** Futuros sin fecha de expiración. El tipo más común en crypto.

```
Particularidad: Funding Rate
- Cada 8 horas se paga/recibe una pequeña tarifa
- Si muchos están en LONG, los LONG pagan a los SHORT
- Si muchos están en SHORT, los SHORT pagan a los LONG
- Esto mantiene el precio del futuro cerca del precio spot
```

---

## 3. Tipos de Órdenes

### Orden de Mercado (Market Order)

**Definición:** Se ejecuta INMEDIATAMENTE al mejor precio disponible.

```
Ventajas:
✓ Ejecución garantizada
✓ Rápida

Desventajas:
✗ No controlas el precio exacto
✗ En mercados con poca liquidez puede haber "slippage"
```

**Uso en SATH:** Para entrar y salir de posiciones rápidamente.

### Orden Límite (Limit Order)

**Definición:** Se ejecuta SOLO cuando el precio llega a tu nivel especificado.

```
Ejemplo:
- SOL está a $140
- Pones orden límite de COMPRA a $130
- La orden se ejecuta solo si SOL baja a $130
- Si nunca llega, la orden no se ejecuta
```

**Uso en SATH:** Para Take Profit en algunos casos.

### Stop Loss (SL)

**Definición:** Orden que cierra tu posición automáticamente para LIMITAR PÉRDIDAS.

```
Ejemplo LONG:
- Compraste SOL a $140
- Pones Stop Loss a $135
- Si SOL baja a $135, se vende automáticamente
- Pérdida limitada: $5 por SOL (3.5%)

Ejemplo SHORT:
- Vendiste (short) SOL a $140
- Pones Stop Loss a $145
- Si SOL SUBE a $145, se cierra automáticamente
- Pérdida limitada: $5 por SOL (3.5%)
```

**Importancia:** Es tu "seguro de vida" en trading. NUNCA operes sin Stop Loss.

### Take Profit (TP)

**Definición:** Orden que cierra tu posición automáticamente para ASEGURAR GANANCIAS.

```
Ejemplo LONG:
- Compraste SOL a $140
- Pones Take Profit a $160
- Si SOL sube a $160, se vende automáticamente
- Ganancia asegurada: $20 por SOL (14.3%)
```

### Orden OCO (One-Cancels-Other)

**Definición:** Combina Stop Loss y Take Profit. Cuando uno se ejecuta, el otro se cancela.

```
┌──────────────────────────────────────────────────────┐
│                    ORDEN OCO                         │
│                                                      │
│     Take Profit: $160  ←── Si llega aquí, VENDE     │
│           ↑                                          │
│           │                                          │
│     Precio actual: $140                              │
│           │                                          │
│           ↓                                          │
│     Stop Loss: $135    ←── Si llega aquí, VENDE     │
│                                                      │
│  → Cuando uno se ejecuta, el otro se CANCELA        │
└──────────────────────────────────────────────────────┘
```

**Uso en SATH:** En modo LIVE, el bot crea órdenes OCO reales en Binance.

### Trailing Stop

**Definición:** Stop Loss que se MUEVE automáticamente siguiendo el precio favorable.

```
Ejemplo (LONG con Trailing Stop de 5%):

Precio   │  Trailing Stop  │  Nota
─────────┼────────────────┼──────────────────
$100     │  $95           │  Inicial (5% abajo)
$110     │  $104.50       │  Subió! SL sube también
$120     │  $114          │  SL sigue subiendo
$115     │  $114          │  Precio baja, SL NO baja
$114     │  EJECUTADO     │  Tocó el trailing stop

Ganancia: $14 (14%) en vez de $0 si solo tenías SL fijo en $95
```

**Uso en SATH:** Opcional, configurable con `trailing_enabled`.

---

## 4. Posiciones y Direcciones

### Posición LONG (Compra)

**Definición:** Apuestas a que el precio SUBIRÁ.

```
Mecánica:
1. COMPRAS el activo a precio actual
2. Esperas que el precio SUBA
3. VENDES a precio más alto
4. Ganancia = Precio Venta - Precio Compra

Ejemplo:
- Compras 1 ETH a $2,000
- Precio sube a $2,500
- Vendes
- Ganancia: $500
```

### Posición SHORT (Venta en Corto)

**Definición:** Apuestas a que el precio BAJARÁ.

```
Mecánica (simplificada):
1. "PIDES PRESTADO" el activo y lo vendes inmediatamente
2. Esperas que el precio BAJE
3. COMPRAS el activo más barato
4. Devuelves lo prestado
5. Te quedas con la diferencia

Ejemplo:
- "Vendes" 1 ETH a $2,500 (prestado)
- Precio baja a $2,000
- Compras 1 ETH a $2,000
- Devuelves el ETH prestado
- Ganancia: $500
```

**Nota:** En futuros, el "préstamo" es automático y transparente.

### Resumen Visual

```
           LONG                              SHORT
    ┌───────────────┐                 ┌───────────────┐
    │   COMPRAS     │                 │    VENDES     │
    │   PRIMERO     │                 │    PRIMERO    │
    │      ↓        │                 │      ↓        │
    │  Precio SUBE  │    vs           │  Precio BAJA  │
    │      ↓        │                 │      ↓        │
    │   VENDES      │                 │   COMPRAS     │
    │   DESPUÉS     │                 │   DESPUÉS     │
    │      =        │                 │      =        │
    │   GANANCIA    │                 │   GANANCIA    │
    └───────────────┘                 └───────────────┘
```

---

## 5. Gestión de Riesgo

### ¿Por qué es Importante?

> "Los traders profesionales no se enfocan en cuánto pueden ganar,
> sino en cuánto pueden perder."

El 95% de los traders pierden dinero. La diferencia entre el 5% ganador es la **gestión de riesgo**.

### Conceptos Clave

#### Riesgo por Operación

**Definición:** Porcentaje máximo de tu capital que puedes perder en UNA operación.

```
Regla común: Máximo 1-2% por operación

Ejemplo:
- Capital total: $10,000
- Riesgo por operación: 2%
- Máxima pérdida por trade: $200

Esto significa:
- Puedes perder 50 trades seguidos antes de quebrar
- Estadísticamente muy difícil si tu sistema tiene algo de lógica
```

**En SATH:** Configurable con `max_risk_per_trade` (default: 2%)

#### Drawdown

**Definición:** Caída porcentual desde el punto más alto de tu capital.

```
Ejemplo:
- Capital inicial: $10,000
- Sube a: $12,000 (nuevo máximo)
- Baja a: $10,800
- Drawdown: ($12,000 - $10,800) / $12,000 = 10%

Visualización:
$12,000 ──●─────────────────── Máximo histórico
          │
          │  ← Drawdown 10%
          │
$10,800 ──●─────────────────── Punto actual
```

**En SATH:** Se detiene el trading si drawdown > `max_drawdown` (default: 10%)

#### Risk/Reward Ratio (R/R o R:R)

**Definición:** Proporción entre lo que arriesgas y lo que puedes ganar.

```
Fórmula:
R/R = Ganancia Potencial / Pérdida Potencial

Ejemplo:
- Entrada: $100
- Stop Loss: $95 (arriesgas $5)
- Take Profit: $115 (puedes ganar $15)
- R/R = $15 / $5 = 3:1 (o 3.0)

Interpretación:
- R/R de 3:1 significa que ganas 3 veces lo que arriesgas
- Con R/R de 3:1, puedes ganar solo el 25% de trades y aún ser rentable
```

**En SATH:** Mínimo R/R configurable con `min_risk_reward_ratio` (default: 2.0)

#### Tabla de R/R vs Win Rate Necesario

| R/R Ratio | Win Rate Mínimo para ser Rentable |
|-----------|-----------------------------------|
| 1:1       | 51%                               |
| 1.5:1     | 40%                               |
| 2:1       | 34%                               |
| 3:1       | 26%                               |
| 4:1       | 21%                               |

### El Criterio de Kelly

**Definición:** Fórmula matemática para calcular el tamaño ÓPTIMO de posición.

```
Fórmula:
Kelly % = (bp - q) / b

Donde:
- b = ratio de ganancia/pérdida (R/R)
- p = probabilidad de ganar
- q = probabilidad de perder (1 - p)

Ejemplo:
- R/R = 2 (b = 2)
- Win Rate = 50% (p = 0.5)
- q = 0.5

Kelly = (2 × 0.5 - 0.5) / 2
Kelly = (1 - 0.5) / 2
Kelly = 0.25 = 25%

Significa: Deberías arriesgar 25% de tu capital en cada trade.
```

**En SATH:** Se usa Kelly "fraccional" (usualmente Kelly/2 o Kelly/4) para ser más conservador.

### Position Sizing (Tamaño de Posición)

**Definición:** Cuánto dinero poner en cada operación.

```
Fórmula básica:
Tamaño = (Capital × Riesgo%) / Distancia al SL

Ejemplo:
- Capital: $10,000
- Riesgo por trade: 2% = $200
- Precio entrada: $100
- Stop Loss: $95
- Distancia SL: 5% ($5)

Cantidad a comprar = $200 / $5 = 40 unidades
Valor de posición = 40 × $100 = $4,000

Si el SL se activa:
Pérdida = 40 × $5 = $200 = 2% del capital ✓
```

---

## 6. Análisis Técnico

### ¿Qué es el Análisis Técnico?

**Definición:** Estudio de gráficos de precios y volumen para predecir movimientos futuros.

**Principios fundamentales:**
1. El precio descuenta todo (la información ya está reflejada)
2. Los precios se mueven en tendencias
3. La historia tiende a repetirse

### Soporte y Resistencia

#### Soporte

**Definición:** Nivel de precio donde hay suficiente demanda para detener una caída.

```
Precio
  │
  │     ╱╲      ╱╲
  │    ╱  ╲    ╱  ╲
  │   ╱    ╲  ╱    ╲
  │──●──────●──────●───── SOPORTE ($95)
  │         El precio "rebota" aquí
  │
  └────────────────────────────────
```

#### Resistencia

**Definición:** Nivel de precio donde hay suficiente oferta para detener una subida.

```
Precio
  │
  │──●──────●──────●───── RESISTENCIA ($105)
  │   ╲    ╱  ╲    ╱
  │    ╲  ╱    ╲  ╱
  │     ╲╱      ╲╱
  │         El precio "choca" aquí
  │
  └────────────────────────────────
```

### Tendencias

#### Tendencia Alcista (Bullish/Uptrend)

```
Precio
  │                    ╱
  │                 ╱ ╱
  │              ╱ ╱
  │           ╱ ╱      Máximos más altos
  │        ╱ ╱         Mínimos más altos
  │     ╱ ╱
  │  ╱ ╱
  │╱ ╱
  └────────────────────────────────
                               Tiempo
```

#### Tendencia Bajista (Bearish/Downtrend)

```
Precio
  │╲ ╲
  │  ╲ ╲
  │     ╲ ╲
  │        ╲ ╲         Máximos más bajos
  │           ╲ ╲      Mínimos más bajos
  │              ╲ ╲
  │                 ╲ ╲
  │                    ╲
  └────────────────────────────────
                               Tiempo
```

#### Tendencia Lateral (Ranging/Sideways)

```
Precio
  │
  │───────────────────── Resistencia
  │   ╱╲    ╱╲    ╱╲
  │  ╱  ╲  ╱  ╲  ╱  ╲
  │ ╱    ╲╱    ╲╱    ╲
  │───────────────────── Soporte
  │   El precio oscila entre dos niveles
  └────────────────────────────────
```

### Breakout (Ruptura)

**Definición:** Cuando el precio rompe un nivel de soporte o resistencia importante.

```
           BREAKOUT ALCISTA
Precio
  │              ╱
  │             ╱
  │────────────●───── Resistencia ROTA
  │     ╱╲    ╱
  │    ╱  ╲  ╱
  │   ╱    ╲╱
  │
  └────────────────────────────────

           BREAKOUT BAJISTA
Precio
  │   ╲    ╱╲
  │    ╲  ╱  ╲
  │     ╲╱    ╲
  │────────────●───── Soporte ROTO
  │             ╲
  │              ╲
  │
  └────────────────────────────────
```

---

## 7. Indicadores Técnicos

### ¿Qué son los Indicadores?

**Definición:** Cálculos matemáticos basados en precio, volumen y/o interés abierto que ayudan a identificar oportunidades.

### Indicadores de Tendencia

#### Media Móvil Simple (SMA)

**Definición:** Promedio de los últimos N precios de cierre.

```
Fórmula:
SMA(N) = (P1 + P2 + ... + PN) / N

Ejemplo SMA(5):
Precios de cierre: $100, $102, $98, $103, $101
SMA(5) = (100 + 102 + 98 + 103 + 101) / 5 = $100.80
```

**Interpretación:**
- Precio > SMA = Tendencia alcista
- Precio < SMA = Tendencia bajista

#### Media Móvil Exponencial (EMA)

**Definición:** Como SMA pero da más peso a precios recientes.

```
EMA es más "rápida" que SMA
- Reacciona más rápido a cambios de precio
- Mejor para trading a corto plazo

Uso común:
- EMA(9) y EMA(21) para corto plazo
- EMA(50) y EMA(200) para largo plazo
```

**Cruce de Medias (Golden/Death Cross):**
```
GOLDEN CROSS (señal alcista):
EMA rápida cruza ARRIBA de EMA lenta

  │     EMA(9)──────●
  │              ╱
  │           ╱
  │        ╱
  │     ╱   EMA(21)──────
  │  ●
  └────────────────────────

DEATH CROSS (señal bajista):
EMA rápida cruza ABAJO de EMA lenta
```

**En SATH:** Se usan EMA(8) y EMA(21) para detección de tendencia.

### Indicadores de Momentum

#### RSI (Relative Strength Index)

**Definición:** Mide la velocidad y magnitud de los movimientos de precio. Oscila entre 0 y 100.

```
Zonas:
┌─────────────────────────────────┐
│ RSI > 70 = SOBRECOMPRADO        │ ← Posible reversión a la baja
├─────────────────────────────────┤
│ RSI 30-70 = ZONA NEUTRAL        │
├─────────────────────────────────┤
│ RSI < 30 = SOBREVENDIDO         │ ← Posible reversión al alza
└─────────────────────────────────┘
```

**Divergencias RSI:**
```
DIVERGENCIA ALCISTA (señal de compra):
- Precio hace mínimos más bajos
- RSI hace mínimos más altos
- El momentum bajista se está debilitando

Precio:  ╲    ╱╲
          ╲  ╱  ╲
           ╲╱    ╲  ← Mínimo más bajo
                  ╲

RSI:     ╲      ╱
          ╲    ╱   ← Mínimo más alto
           ╲  ╱
            ╲╱
```

**En SATH:** RSI se usa con período 14, umbrales configurables.

#### MACD (Moving Average Convergence Divergence)

**Definición:** Muestra la relación entre dos EMAs y su momentum.

```
Componentes:
1. MACD Line = EMA(12) - EMA(26)
2. Signal Line = EMA(9) del MACD Line
3. Histogram = MACD Line - Signal Line

Señales:
┌──────────────────────────────────────────┐
│ MACD cruza ARRIBA de Signal = COMPRAR    │
│ MACD cruza ABAJO de Signal = VENDER      │
│                                          │
│ Histogram creciente = Momentum alcista   │
│ Histogram decreciente = Momentum bajista │
└──────────────────────────────────────────┘
```

**En SATH:** MACD con parámetros estándar (12, 26, 9).

### Indicadores de Volatilidad

#### ATR (Average True Range)

**Definición:** Mide la volatilidad promedio del precio.

```
True Range = Máximo de:
- High actual - Low actual
- |High actual - Close anterior|
- |Low actual - Close anterior|

ATR = Promedio del True Range de los últimos N períodos

Uso práctico:
- ATR alto = Alta volatilidad (más riesgo, más oportunidad)
- ATR bajo = Baja volatilidad (mercado tranquilo)
- Se usa para calcular Stop Loss dinámicos
```

**En SATH:** ATR para calcular SL/TP dinámicos basados en volatilidad.

```
Ejemplo de SL con ATR:
- ATR(14) = $5
- Multiplicador SL = 1.5
- Stop Loss = Precio entrada ± (ATR × 1.5)
- Si entrada = $100: SL = $100 - $7.50 = $92.50
```

#### Bollinger Bands

**Definición:** Bandas que envuelven el precio, basadas en desviación estándar.

```
Componentes:
- Banda superior = SMA(20) + (2 × Desviación Estándar)
- Banda media = SMA(20)
- Banda inferior = SMA(20) - (2 × Desviación Estándar)

    Banda Superior ─────────────────────
                      ╲  ╱╲    ╱╲
    Banda Media ───────╲╱──╲──╱──╲─────
                             ╲╱
    Banda Inferior ─────────────────────

Interpretación:
- Precio toca banda superior = Posible sobrecompra
- Precio toca banda inferior = Posible sobreventa
- Bandas se contraen = Baja volatilidad, posible breakout próximo
- Bandas se expanden = Alta volatilidad
```

**En SATH:** Bollinger Bands para detectar extremos y volatilidad.

### Indicadores de Volumen

#### OBV (On-Balance Volume)

**Definición:** Suma acumulativa de volumen según la dirección del precio.

```
Cálculo:
- Si precio cierra arriba: OBV = OBV anterior + Volumen
- Si precio cierra abajo: OBV = OBV anterior - Volumen
- Si precio cierra igual: OBV = OBV anterior

Interpretación:
- OBV sube mientras precio sube = Tendencia fuerte
- OBV diverge del precio = Posible reversión
```

#### VWAP (Volume Weighted Average Price)

**Definición:** Precio promedio ponderado por volumen.

```
VWAP = Σ(Precio × Volumen) / Σ(Volumen)

Uso:
- Precio > VWAP = Tendencia alcista intradiaria
- Precio < VWAP = Tendencia bajista intradiaria
- Usado por instituciones como referencia
```

---

## 8. Patrones de Velas (Candlesticks)

### Anatomía de una Vela

```
        Vela ALCISTA (Verde)          Vela BAJISTA (Roja)

             │ Mecha                        │ Mecha
             │ Superior                     │ Superior
        ┌────┴────┐ Cierre            ┌────┴────┐ Apertura
        │█████████│                   │░░░░░░░░░│
        │█████████│ Cuerpo            │░░░░░░░░░│ Cuerpo
        │█████████│                   │░░░░░░░░░│
        └────┬────┘ Apertura          └────┬────┘ Cierre
             │ Mecha                        │ Mecha
             │ Inferior                     │ Inferior

   Precio subió (Cierre > Apertura)   Precio bajó (Cierre < Apertura)
```

### Patrones de Reversión

#### Martillo (Hammer)

```
Señal: ALCISTA (en tendencia bajista)

     │
     │      Cuerpo pequeño arriba
  ┌──┴──┐
  │     │
  └──┬──┘
     │
     │     Mecha inferior larga
     │     (2-3x el cuerpo)
     │

Significado: Vendedores empujaron precio abajo,
pero compradores lo recuperaron.
```

#### Estrella Fugaz (Shooting Star)

```
Señal: BAJISTA (en tendencia alcista)

     │
     │     Mecha superior larga
     │     (2-3x el cuerpo)
     │
  ┌──┴──┐
  │     │
  └──┬──┘  Cuerpo pequeño abajo
     │

Significado: Compradores empujaron precio arriba,
pero vendedores lo rechazaron.
```

#### Doji

```
Señal: INDECISIÓN

     │
     │
  ───┼───  Apertura ≈ Cierre
     │
     │

Significado: Ni compradores ni vendedores dominan.
Posible reversión si aparece en extremos.
```

### Patrones de Continuación

#### Tres Soldados Blancos (Three White Soldiers)

```
Señal: Continuación ALCISTA fuerte

              ┌───┐
              │███│
           ┌──┴───┴──┐
           │█████████│
        ┌──┴─────────┴──┐
        │███████████████│
        └───────────────┘

Tres velas alcistas consecutivas con cierres progresivamente más altos.
```

#### Tres Cuervos Negros (Three Black Crows)

```
Señal: Continuación BAJISTA fuerte

        ┌───────────────┐
        │░░░░░░░░░░░░░░░│
        └──┬─────────┬──┘
           │░░░░░░░░░│
           └──┬───┬──┘
              │░░░│
              └───┘

Tres velas bajistas consecutivas con cierres progresivamente más bajos.
```

---

## 9. Timeframes (Marcos Temporales)

### ¿Qué es un Timeframe?

**Definición:** El período de tiempo que representa cada vela en un gráfico.

```
Timeframes comunes:
┌────────────┬─────────────────────────────────────┐
│ Timeframe  │ Cada vela representa                │
├────────────┼─────────────────────────────────────┤
│ 1m         │ 1 minuto                            │
│ 5m         │ 5 minutos                           │
│ 15m        │ 15 minutos                          │
│ 1h         │ 1 hora                              │
│ 4h         │ 4 horas                             │
│ 1d         │ 1 día                               │
│ 1w         │ 1 semana                            │
└────────────┴─────────────────────────────────────┘
```

### Análisis Multi-Temporal (MTF)

**Definición:** Analizar el mismo activo en múltiples timeframes para confirmar señales.

```
Regla general:
- Timeframe alto → Define la TENDENCIA principal
- Timeframe medio → Confirma la señal
- Timeframe bajo → Timing de ENTRADA preciso

Ejemplo configuración SATH:
┌───────────────────────────────────────────────────┐
│ Timeframe Alto (4h):  Tendencia = ALCISTA        │
│ Timeframe Medio (1h): Señal = COMPRA confirmada  │
│ Timeframe Bajo (15m): Entrada precisa            │
│                                                   │
│ → Solo operar LONG porque todos están alineados  │
└───────────────────────────────────────────────────┘
```

**En SATH:** MTF Analysis con timeframes configurables y peso por timeframe.

---

## 10. Conceptos de Criptomonedas

### Términos Específicos de Crypto

| Término | Definición |
|---------|------------|
| **Wallet** | Billetera digital para guardar criptomonedas |
| **Exchange** | Plataforma para comprar/vender crypto (Binance, Coinbase) |
| **Altcoin** | Cualquier criptomoneda que no sea Bitcoin |
| **Stablecoin** | Crypto con precio "estable" (USDT, USDC ≈ $1) |
| **Market Cap** | Valor total de todas las monedas en circulación |
| **FUD** | Fear, Uncertainty, Doubt - Noticias negativas |
| **FOMO** | Fear Of Missing Out - Miedo a perderse la subida |
| **HODL** | Hold On for Dear Life - Mantener a largo plazo |
| **Whale** | Inversor con grandes cantidades de crypto |
| **Pump & Dump** | Manipulación de precio (subir y vender) |

### Binance Específico

| Término | Definición |
|---------|------------|
| **Spot Wallet** | Wallet para trading spot |
| **Futures Wallet** | Wallet para trading de futuros |
| **Margin** | Colateral para abrir posiciones apalancadas |
| **Cross Margin** | Todo el balance como colateral |
| **Isolated Margin** | Solo parte del balance como colateral |
| **Liquidation** | Cierre forzado cuando pierdes demasiado margen |
| **Funding Rate** | Pago periódico entre longs y shorts |

### Apalancamiento y Liquidación

```
Ejemplo con 10x de apalancamiento:

Capital: $1,000
Apalancamiento: 10x
Posición: $10,000 en BTC

Si BTC sube 10%:
- Posición vale: $11,000
- Ganancia: $1,000 (100% de tu capital!)

Si BTC baja 10%:
- Posición vale: $9,000
- Pérdida: $1,000 (100% de tu capital)
- LIQUIDACIÓN: Pierdes todo

┌─────────────────────────────────────────────────┐
│ Precio Liquidación ≈ Entrada × (1 - 1/Leverage) │
│                                                 │
│ Con 10x: Liquidación si precio baja ~10%        │
│ Con 20x: Liquidación si precio baja ~5%         │
│ Con 50x: Liquidación si precio baja ~2%         │
│ Con 100x: Liquidación si precio baja ~1%        │
└─────────────────────────────────────────────────┘
```

**En SATH:** Apalancamiento conservador (default: 5x), nunca más de 10x.

---

## 11. Trading Algorítmico

### ¿Qué es un Bot de Trading?

**Definición:** Software que ejecuta operaciones automáticamente según reglas predefinidas.

```
Flujo básico de un bot:
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐ │
│  │ Obtener │ →  │ Analizar │ →  │ Decidir │ →  │ Ejecutar│ │
│  │  Datos  │    │  Datos   │    │ Comprar │    │  Orden  │ │
│  │(Precios)│    │(Indicad.)│    │ o Vender│    │(Exchange│ │
│  └─────────┘    └──────────┘    └─────────┘    └─────────┘ │
│       ↑                                             │       │
│       └─────────────── Loop cada X tiempo ──────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Ventajas del Trading Algorítmico

| Ventaja | Descripción |
|---------|-------------|
| **Sin emociones** | No tiene miedo ni codicia |
| **24/7** | Opera mientras duermes |
| **Velocidad** | Ejecuta en milisegundos |
| **Disciplina** | Sigue las reglas siempre |
| **Backtesting** | Puedes probar estrategias con datos históricos |

### Desventajas y Riesgos

| Riesgo | Descripción |
|--------|-------------|
| **Bugs** | Errores de código pueden causar pérdidas |
| **Overfitting** | Estrategia funciona en backtest pero no en real |
| **Black Swan** | Eventos extremos no previstos |
| **Latencia** | Retrasos en conexión pueden afectar |
| **Mercados cambian** | Lo que funcionaba puede dejar de funcionar |

### Backtesting vs Paper Trading vs Live

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  BACKTESTING          PAPER TRADING         LIVE TRADING        │
│  ────────────         ─────────────         ────────────        │
│                                                                 │
│  Datos históricos     Datos en tiempo real  Datos en tiempo real│
│  Órdenes simuladas    Órdenes simuladas     Órdenes REALES      │
│  Sin dinero real      Sin dinero real       DINERO REAL         │
│                                                                 │
│  Para: Desarrollar    Para: Validar que     Para: Producción    │
│        estrategias          todo funciona                       │
│                                                                 │
│  ←────────────── Progresión recomendada ──────────────→         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. Términos Específicos de SATH

### Arquitectura SATH

```
┌────────────────────────────────────────────────────────────────┐
│                         SATH BOT                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Market     │  │  Technical   │  │    Risk      │         │
│  │   Scanner    │  │  Analyzer    │  │   Manager    │         │
│  │              │  │              │  │              │         │
│  │ Busca pares  │  │ Calcula      │  │ Kelly, SL,   │         │
│  │ con volumen  │  │ indicadores  │  │ position     │         │
│  │ y momentum   │  │ y señales    │  │ sizing       │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           ▼                                    │
│                  ┌──────────────┐                              │
│                  │   Position   │                              │
│                  │    Engine    │                              │
│                  │              │                              │
│                  │ Ejecuta y    │                              │
│                  │ monitorea    │                              │
│                  │ posiciones   │                              │
│                  └──────────────┘                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Glosario de Términos SATH

| Término | Módulo | Significado |
|---------|--------|-------------|
| **MTF Analysis** | Technical | Multi-TimeFrame Analysis - Análisis en múltiples timeframes |
| **Confidence** | Technical | Nivel de confianza de la señal (0-1) |
| **Alignment Score** | Technical | Qué tan alineados están los timeframes (0-1) |
| **Win Probability** | Risk | Probabilidad de ganar ajustada por historial |
| **Kelly Fraction** | Risk | Porcentaje de capital a arriesgar (Kelly) |
| **Protection Mode** | Position | Modo de protección: 'oco' o 'local' |
| **Trading Decision** | Core | Decisión final: LONG, SHORT, o NEUTRAL |
| **Paper Mode** | Core | Modo simulación sin dinero real |
| **ATR Multiplier** | Risk | Multiplicador de ATR para calcular SL |

### Flujo de una Decisión en SATH

```
1. ESCANEO DE MERCADO
   │
   ├── ¿Hay volatilidad suficiente? ──No──→ SKIP
   ├── ¿Hay volumen suficiente? ──No──→ SKIP
   ├── ¿Ya tenemos posición abierta? ──Sí──→ SKIP
   │
   ▼
2. ANÁLISIS TÉCNICO
   │
   ├── Calcular indicadores (RSI, MACD, BB, EMA, ATR)
   ├── Analizar cada timeframe
   ├── Calcular alignment score
   ├── Detectar divergencias
   ├── Verificar patrones de velas
   │
   ▼
3. GENERACIÓN DE SEÑAL
   │
   ├── Dirección: LONG, SHORT, o NEUTRAL
   ├── Confianza: 0.0 a 1.0
   ├── Stop Loss sugerido
   ├── Take Profit sugerido
   │
   ▼
4. GESTIÓN DE RIESGO
   │
   ├── ¿Confianza > mínimo requerido? ──No──→ SKIP
   ├── Calcular R/R ratio
   ├── ¿R/R > mínimo requerido? ──No──→ SKIP
   ├── Calcular tamaño de posición (Kelly)
   ├── ¿Tamaño >= mínimo rentable? ──No──→ SKIP
   ├── ¿Drawdown < máximo permitido? ──No──→ STOP
   │
   ▼
5. EJECUCIÓN
   │
   ├── Abrir posición
   ├── Crear órdenes OCO (SL + TP)
   ├── Registrar en base de datos
   ├── Iniciar monitoreo
   │
   ▼
6. MONITOREO (loop cada 0.5 segundos)
   │
   ├── Verificar si SL/TP alcanzado
   ├── Actualizar trailing stop (si activo)
   ├── Registrar métricas
   │
   ▼
7. CIERRE
   │
   ├── Registrar resultado
   ├── Actualizar estadísticas
   ├── Calcular nuevo Kelly basado en historial
   │
   ▼
   LISTO PARA PRÓXIMO CICLO
```

---

## 13. Fórmulas Importantes

### Fórmulas de Rendimiento

```python
# Profit/Loss (PnL)
PnL_LONG = (Precio_Salida - Precio_Entrada) × Cantidad
PnL_SHORT = (Precio_Entrada - Precio_Salida) × Cantidad

# Retorno porcentual
Retorno% = (PnL / Inversión_Inicial) × 100

# Retorno con apalancamiento
Retorno_Apalancado% = Retorno% × Apalancamiento
```

### Fórmulas de Riesgo

```python
# Risk/Reward Ratio
R_R = |Precio_TP - Precio_Entrada| / |Precio_Entrada - Precio_SL|

# Kelly Criterion
Kelly% = (b × p - q) / b
# donde:
#   b = R/R ratio
#   p = probabilidad de ganar
#   q = probabilidad de perder (1 - p)

# Position Size (basado en riesgo fijo)
Tamaño = (Capital × Riesgo%) / |Precio_Entrada - Precio_SL|

# Drawdown
Drawdown% = (Máximo_Histórico - Valor_Actual) / Máximo_Histórico × 100
```

### Fórmulas de Indicadores

```python
# RSI
RS = Promedio_Ganancias / Promedio_Pérdidas
RSI = 100 - (100 / (1 + RS))

# ATR
True_Range = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
ATR = SMA(True_Range, período)

# Bollinger Bands
Banda_Media = SMA(Close, 20)
Banda_Superior = Banda_Media + (2 × StdDev)
Banda_Inferior = Banda_Media - (2 × StdDev)

# MACD
MACD_Line = EMA(12) - EMA(26)
Signal_Line = EMA(MACD_Line, 9)
Histogram = MACD_Line - Signal_Line
```

---

## 14. Ejemplos Prácticos

### Ejemplo 1: Análisis de una Operación LONG

```
SITUACIÓN:
- SOL/USDT @ $140.00
- RSI(14) = 35 (saliendo de sobreventa)
- EMA(8) cruza arriba de EMA(21)
- Volumen aumentando
- ATR(14) = $4.50

CÁLCULOS:

1. Señal: LONG (alcista)
   - RSI rebotando desde sobreventa ✓
   - Cruce de medias alcista ✓
   - Volumen confirma ✓

2. Stop Loss (1.5 × ATR):
   SL = $140.00 - (1.5 × $4.50) = $133.25

3. Take Profit (R/R = 2.5):
   Riesgo = $140.00 - $133.25 = $6.75
   Reward = $6.75 × 2.5 = $16.875
   TP = $140.00 + $16.875 = $156.88

4. Position Sizing:
   - Capital: $10,000
   - Riesgo: 2% = $200
   - Tamaño = $200 / $6.75 = 29.6 SOL
   - Valor posición = 29.6 × $140 = $4,144

5. Si se activa TP:
   Ganancia = 29.6 × $16.875 = $499.50 (+5% del capital)

6. Si se activa SL:
   Pérdida = 29.6 × $6.75 = $199.80 (-2% del capital)
```

### Ejemplo 2: Análisis Multi-Timeframe

```
PAR: ETH/USDT

TIMEFRAME 4H (Tendencia principal):
├── Tendencia: ALCISTA
├── Precio > EMA(50)
├── RSI: 58 (neutral-alcista)
└── Peso: 40%

TIMEFRAME 1H (Confirmación):
├── Tendencia: ALCISTA
├── MACD cruzando hacia arriba
├── RSI: 52
└── Peso: 35%

TIMEFRAME 15M (Entrada):
├── Tendencia: ALCISTA
├── Precio rebotando de soporte
├── RSI: 45 (buen punto de entrada)
└── Peso: 25%

CÁLCULO DE ALIGNMENT:
- 4H Alcista × 0.40 = 0.40
- 1H Alcista × 0.35 = 0.35
- 15M Alcista × 0.25 = 0.25
- TOTAL = 1.00 (100% alineado)

DECISIÓN: LONG con alta confianza
```

### Ejemplo 3: Gestión de Riesgo con Kelly

```
HISTORIAL DEL BOT (últimos 50 trades):
- Trades ganadores: 28 (56%)
- Trades perdedores: 22 (44%)
- R/R promedio ganadores: 2.2
- R/R promedio perdedores: 1.0

CÁLCULO KELLY:
p = 0.56 (probabilidad de ganar)
q = 0.44 (probabilidad de perder)
b = 2.2 (ratio de ganancia)

Kelly% = (2.2 × 0.56 - 0.44) / 2.2
Kelly% = (1.232 - 0.44) / 2.2
Kelly% = 0.792 / 2.2
Kelly% = 0.36 = 36%

AJUSTE CONSERVADOR (Kelly/3):
Riesgo por trade = 36% / 3 = 12%

APLICACIÓN:
- Capital: $10,000
- Riesgo máximo: 12% = $1,200
- Pero limitado por max_risk_per_trade = 2%
- Riesgo real: $200

El Kelly sugiere que podríamos arriesgar más,
pero los límites de seguridad lo mantienen conservador.
```

---

## Conclusión

Este documento cubre los conceptos fundamentales necesarios para entender el trading algorítmico y el funcionamiento del bot SATH. Los puntos clave a recordar:

1. **Gestión de riesgo es primordial** - Nunca arriesgues más del 2% por operación
2. **El análisis técnico es una herramienta, no una garantía** - Las señales son probabilísticas
3. **Paper trading antes de live** - Siempre valida en simulación primero
4. **Mantén registros** - Analiza tus operaciones para mejorar
5. **El mercado siempre tiene razón** - Respeta los stop loss

---

*Documento generado para SATH Bot v1.7+ | Última actualización: Diciembre 2024*
