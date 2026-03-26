Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
finally {
    Pop-Location
}
