# PowerShell script to create a default SUPER_ADMIN user
$baseUrl = "http://localhost:8001"
$adminEmail = "admin@example.com"
$adminPassword = "Password123!"
$adminFullName = "Platform Super Admin"

function Log($msg) { Write-Host "[INFO] $msg" }
function LogError($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

$body = @{
    email = $adminEmail
    password = $adminPassword
    role = "SUPER_ADMIN"
    full_name = $adminFullName
    photo_url = $null
}

Log "Creating admin user via /api/auth/register"
try {
    $resp = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/auth/register" -Body ($body | ConvertTo-Json) -ContentType "application/json" -ErrorAction Stop
    Log "✅ Admin user created: $($resp.message)"
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Log "⚠️ Admin user may already exist – proceeding."
    } else {
        LogError "Failed to create admin user: $_"
        exit 1
    }
}
