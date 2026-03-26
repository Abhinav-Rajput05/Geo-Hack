Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

docker compose up -d redis
docker compose ps redis
