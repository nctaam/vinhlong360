param(
  [string]$Phone = "0909090909",
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Script:Failures = 0
$Script:Warnings = 0

function Write-Check {
  param([string]$Name, [string]$Status, [string]$Detail = "")
  $prefix = switch ($Status) {
    "OK" { "[OK]" }
    "WARN" { "[WARN]" }
    default { "[FAIL]" }
  }
  if ($Status -eq "FAIL") { $Script:Failures++ }
  if ($Status -eq "WARN") { $Script:Warnings++ }
  if ($Detail) { Write-Host "$prefix $Name - $Detail" } else { Write-Host "$prefix $Name" }
}

function Read-DotEnvValue {
  param([string]$Key)
  $envPath = Join-Path $PSScriptRoot "..\.env"
  if (!(Test-Path -LiteralPath $envPath)) { return $null }
  foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match "^\s*#") { continue }
    if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.+?)\s*$") {
      return $Matches[1].Trim('"').Trim("'")
    }
  }
  return $null
}

function Mask-DatabaseUrl {
  param([string]$Value)
  if (!$Value) { return "" }
  return ($Value -replace "://([^:@/]+):([^@/]+)@", '://$1:****@')
}

if (!$env:DATABASE_URL) {
  $fromEnvFile = Read-DotEnvValue "DATABASE_URL"
  if ($fromEnvFile) { $env:DATABASE_URL = $fromEnvFile }
}

if (!$env:DATABASE_URL) {
  Write-Check "DATABASE_URL" "FAIL" "missing in environment and .env"
} elseif ($env:DATABASE_URL -notmatch "^postgresql://") {
  Write-Check "DATABASE_URL" "FAIL" "must start with postgresql://, got $(Mask-DatabaseUrl $env:DATABASE_URL)"
} else {
  Write-Check "DATABASE_URL" "OK" "$(Mask-DatabaseUrl $env:DATABASE_URL)"
}

try {
  $driver = & $Python -c "import psycopg2; print('psycopg2 ok')" 2>&1
  $driverExit = $LASTEXITCODE
} catch {
  $driver = $_.Exception.Message
  $driverExit = 1
}
if ($driverExit -ne 0) {
  Write-Check "psycopg2 driver" "FAIL" "install psycopg2-binary in the backend environment"
} else {
  Write-Check "psycopg2 driver" "OK"
}

if ($Script:Failures -eq 0) {
  $env:TEST_AUTH_PHONE = $Phone
  $checkCode = @'
import os
import sys
import psycopg2

dsn = os.environ["DATABASE_URL"]
phone = os.environ.get("TEST_AUTH_PHONE", "0909090909")

try:
    conn = psycopg2.connect(dsn, connect_timeout=5)
except Exception as exc:
    print(f"DB_CONNECT_FAIL {exc.__class__.__name__}: {exc}")
    sys.exit(10)

try:
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("DB_CONNECT_OK")

    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='users'")
    if not cur.fetchone():
        print("SCHEMA_FAIL users table missing")
        sys.exit(20)
    print("SCHEMA_OK users table exists")

    cur.execute("SELECT id::text, COALESCE(username, ''), password_hash IS NOT NULL FROM users WHERE phone=%s", (phone,))
    row = cur.fetchone()
    if not row:
        print(f"ACCOUNT_WARN test account {phone} not found")
        sys.exit(30)
    if not row[2]:
        print(f"ACCOUNT_WARN test account {phone} exists but has no password_hash")
        sys.exit(31)
    print(f"ACCOUNT_OK id={row[0]} username={row[1]} has_password=true")
finally:
    conn.close()
'@

  try {
    $dbResult = $checkCode | & $Python - 2>&1
    $exit = $LASTEXITCODE
  } catch {
    $dbResult = @($_.Exception.Message)
    $exit = 1
  }
  foreach ($line in $dbResult) {
    if ($line -like "DB_CONNECT_OK*") { Write-Check "DB connect" "OK" }
    elseif ($line -like "SCHEMA_OK*") { Write-Check "schema users" "OK" }
    elseif ($line -like "ACCOUNT_OK*") { Write-Check "test account" "OK" $line.Substring("ACCOUNT_OK ".Length) }
    elseif ($line -like "ACCOUNT_WARN*") { Write-Check "test account" "WARN" $line.Substring("ACCOUNT_WARN ".Length) }
    elseif ($line -like "SCHEMA_FAIL*") { Write-Check "schema users" "FAIL" $line.Substring("SCHEMA_FAIL ".Length) }
    elseif ($line -like "DB_CONNECT_FAIL*") { Write-Check "DB connect" "FAIL" $line.Substring("DB_CONNECT_FAIL ".Length) }
    elseif ($line) { Write-Host $line }
  }
} else {
  if (!$env:DATABASE_URL -or $env:DATABASE_URL -notmatch "^postgresql://") {
    Write-Check "DB connect" "FAIL" "skipped because DATABASE_URL is not usable"
  } elseif ($driverExit -ne 0) {
    Write-Check "DB connect" "FAIL" "skipped because psycopg2 driver is unavailable"
  }
  Write-Check "schema users" "FAIL" "skipped because DB connect did not pass"
  Write-Check "test account" "WARN" "skipped because schema check did not pass"
}

if ($Script:Failures -gt 0) {
  Write-Host "Result: FAIL ($Script:Failures failure(s), $Script:Warnings warning(s))"
  exit 1
}

if ($Script:Warnings -gt 0) {
  Write-Host "Result: WARN ($Script:Warnings warning(s))"
  exit 2
}

Write-Host "Result: OK"
