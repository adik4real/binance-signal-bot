app = "binance-signal-bot"
primary_region = "fra"  

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PYTHONUNBUFFERED = "1"
  PORT = "8080"  

[http_service]
  internal_port = 8080  
  force_https = true
  auto_stop_machines = false

  [[http_service.ports]]
    handlers = ["http"]
    port = 80

  [[http_service.ports]]
    handlers = ["tls", "http"]
    port = 443
