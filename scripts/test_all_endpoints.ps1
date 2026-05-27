# PowerShell script to test all API endpoints
# Adjust the base URL and admin credentials as needed
$baseUrl = "http://localhost:8001"
# Seeded SUPER_ADMIN credentials
$adminEmail = "admin@ferwafa.rw"
$adminPassword = "admin123"
# Seeded FERWAFA credentials for FERWAFA endpoints
$ferwafaEmail = "hq@ferwafa.rw"
$ferwafaPassword = "ferwafa123"

function Log($msg)    { Write-Host "[INFO] $msg" }
function LogError($msg){ Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ---------- Auth ----------
Log "Testing authentication endpoints"
# Login as SUPER_ADMIN
$adminLoginBody = "username=$adminEmail&password=$adminPassword"
$adminResp = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/auth/login" `
    -Body $adminLoginBody -ContentType "application/x-www-form-urlencoded" `
    -ErrorAction SilentlyContinue
if ($adminResp -and $adminResp.access_token) {
    $adminToken = $adminResp.access_token
    Log "SUPER_ADMIN login succeeded"
} else {
    LogError "SUPER_ADMIN login failed"
    exit 1
}
# Login as FERWAFA for FERWAFA endpoints
$ferLoginBody = "username=$ferwafaEmail&password=$ferwafaPassword"
$ferResp = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/auth/login" `
    -Body $ferLoginBody -ContentType "application/x-www-form-urlencoded" `
    -ErrorAction SilentlyContinue
if ($ferResp -and $ferResp.access_token) {
    $ferToken = $ferResp.access_token
    Log "FERWAFA login succeeded"
} else {
    LogError "FERWAFA login failed"
    # Continue with only SUPER_ADMIN token; FERWAFA endpoints will be skipped later
}
# Prepare headers
$adminHeaders = @{ Authorization = "Bearer $adminToken" }
$ferwafaHeaders = @{ Authorization = "Bearer $ferToken" }

# Use adminHeaders for admin routes
$headers = $adminHeaders

# ---------- Admin Endpoints ----------
$adminEndpoints = @(
    "/api/admin/system/health",
    "/api/admin/system/history",
    "/api/admin/system/database-check",
    "/api/admin/system/error-logs",
    "/api/admin/system/stats",
    "/api/admin/users",
    "/api/admin/users/all",
    "/api/admin/system/settings"
)

foreach ($ep in $adminEndpoints) {
    Log "GET $ep"
    try {
        $resp = Invoke-RestMethod -Method Get -Uri "$baseUrl$ep" -Headers $headers -ErrorAction Stop
        Log "Success: $(ConvertTo-Json $resp -Depth 2)"
    } catch {
        LogError "Failed $ep"
    }
}

# ---------- FERWAFA Endpoints (example) ----------
Log "Testing FERWAFA endpoints"
$ferwafaEndpoints = @(
    "/api/ferwafa/entities",
    "/api/ferwafa/approval/pending",
    "/api/ferwafa/institution/1"   # replace with a valid ID if needed
)
foreach ($ep in $ferwafaEndpoints) {
    Log "GET $ep"
    if ($ferToken) {
        try {
            $resp = Invoke-RestMethod -Method Get -Uri "$baseUrl$ep" -Headers $ferHeaders -ErrorAction Stop
            Log "Success"
        } catch {
            LogError "Failed $ep"
        }
    } else {
        LogError "Skipping $ep – no FERWAFA token"
    }
}

# ---------- Additional Modules (Club, School, Academy) ----------
$moduleEndpoints = @(
    "/api/club/dashboard",
    "/api/school/dashboard",
    "/api/academy/dashboard"
)
foreach ($ep in $moduleEndpoints) {
    Log "GET $ep"
    try {
        $resp = Invoke-RestMethod -Method Get -Uri "$baseUrl$ep" -Headers $headers -ErrorAction Stop
        Log "Success"
    } catch {
        LogError "Failed $ep"
    }
}

# ---------- AI Machine Download ----------
Log "Testing AI Machine download endpoint"
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/api/download/ai-machine" `
        -Headers $headers -OutFile "ai_machine.zip" -ErrorAction Stop
    Log "AI Machine package downloaded (size: $($resp.Content.Length) bytes)"
} catch {
    LogError "AI Machine download failed"
}

Log "Endpoint testing completed"
