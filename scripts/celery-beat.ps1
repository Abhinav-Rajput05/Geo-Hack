Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
    celery -A app.tasks.celery_app beat --loglevel=info
}
finally {
    Pop-Location
}
