Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
    celery -A app.tasks.celery_app worker --loglevel=info
}
finally {
    Pop-Location
}
