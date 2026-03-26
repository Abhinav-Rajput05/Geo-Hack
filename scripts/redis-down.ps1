Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

docker compose stop redis
docker compose rm -f redis
