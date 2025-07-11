app = "binance-signal-bot-s37rbq"
primary_region = "fra"

[build]
  builder = "paketobuildpacks/builder:base"
  # Опционально: укажи Python-билдпак явно
  buildpacks = ["gcr.io/paketo-buildpacks/python"]

[http_service]
  internal_port = 8080
  force_https = true
