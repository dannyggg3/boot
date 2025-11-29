  # Consultar decisiones de las últimas 2 horas
  docker exec sath_influxdb influx query '
  from(bucket:"trading_decisions") 
    |> range(start: -2h) 
    |> filter(fn: (r) => r._measurement == "trading_decision")
    |> limit(n: 20)
  ' --org trading_bot --token $INFLUXDB_TOKEN

  O si el token está en .env:

  # Leer token del .env y consultar
  source /home/ubuntu/boot/.env
  docker exec sath_influxdb influx query '
  from(bucket:"trading_decisions") 
    |> range(start: -1h) 
    |> filter(fn: (r) => r._measurement == "trading_decision")
  ' --org trading_bot --token "$INFLUXDB_TOKEN"

  Consultas útiles:

  # Ver solo decisiones COMPRA/VENTA (no ESPERA)
  docker exec sath_influxdb influx query '
  from(bucket:"trading_decisions") 
    |> range(start: -24h) 
    |> filter(fn: (r) => r._measurement == "trading_decision")
    |> filter(fn: (r) => r.decision == "COMPRA" or r.decision == "VENTA")
  ' --org trading_bot --token "$INFLUXDB_TOKEN"

  # Ver trades ejecutados
  docker exec sath_influxdb influx query '
  from(bucket:"trading_decisions") 
    |> range(start: -24h) 
    |> filter(fn: (r) => r._measurement == "trade_execution")
  ' --org trading_bot --token "$INFLUXDB_TOKEN"

  # Contar decisiones por tipo
  docker exec sath_influxdb influx query '
  from(bucket:"trading_decisions") 
    |> range(start: -24h) 
    |> filter(fn: (r) => r._measurement == "trading_decision")
    |> group(columns: ["decision"])
    |> count()
  ' --org trading_bot --token "$INFLUXDB_TOKEN"

  Acceso Web (Grafana-style):

  # InfluxDB UI está en puerto 8086
  # Abrir en navegador: http://TU_IP_SERVIDOR:8086
  # Usuario: admin
  # Password: (el de tu .env INFLUXDB_PASSWORD)



  ################################################################################
   # Ver si hubo operaciones ejecutadas
  docker logs sath_bot_live 2>&1 | grep -i "EJECUTANDO ORDEN"

  # Ver decisiones de COMPRA o VENTA
  docker logs sath_bot_live 2>&1 | grep -E "(COMPRA|VENTA)" | grep -v ESPERA

  # Ver errores
  docker logs sath_bot_live 2>&1 | grep -i "error"

  # Ver régimen de mercado detectado
  docker logs sath_bot_live 2>&1 | grep "Régimen de mercado"

  # Ver activación de agentes
  docker logs sath_bot_live 2>&1 | grep -i "agente"

  # Ver últimas 100 líneas
  docker logs sath_bot_live --tail 100

  # Ver logs de las últimas 2 horas
  docker logs sath_bot_live --since 2h

  # Ver logs en tiempo real (Ctrl+C para salir)
  docker logs -f sath_bot_live

  # Combinación: errores + operaciones en tiempo real
  docker logs -f sath_bot_live 2>&1 | grep -E "(ERROR|COMPRA|VENTA|EJECUTANDO|error|Error)"

  # Resumen rápido de estados
  docker logs sath_bot_live 2>&1 | grep -E "(Decisión IA|Régimen|EJECUTANDO)" | tail -30

  Script para monitoreo continuo:

  # Guardar como monitor.sh
  watch -n 10 'docker logs sath_bot_live --tail 20 2>&1 | grep -E "(Decisión|Régimen|COMPRA|VENTA|ERROR|Orden)"'


################################################################################
  # Reinicar boot
  docker compose -f docker-compose.live.yml restart trading_bot

  #ver logs
  docker logs sath_bot_live --tail 100

  docker logs -f sath_bot_live


  rm -f logs/*.log && docker compose -f docker-compose.live.yml down && docker compose -f docker-compose.live.yml up -d --build
