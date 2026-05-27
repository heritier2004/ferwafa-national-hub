$serviceName = "postgresql-x64-18"
$pgDir = "C:\Program Files\PostgreSQL\18"
$binPath = "`"$pgDir\bin\postgres.exe`" -D `"$pgDir\data`""
$pgCtl = "`"$pgDir\bin\pg_ctl.exe`""
$pgData = "$pgDir\data"
$pidFile = "$pgData\postmaster.pid"

Write-Host "Attempting to manage PostgreSQL service..."

# Robust Cleanup of Stale PID file
if (Test-Path $pidFile) {
    Write-Host "Found existing postmaster.pid file. Verifying if process is still active..."
    try {
        $stalePid = (Get-Content $pidFile -TotalCount 1).Trim()
        if ($stalePid -match '^\d+$') {
            $proc = Get-Process -Id [int]$stalePid -ErrorAction SilentlyContinue
            if (!$proc -or $proc.Name -ne "postgres") {
                Write-Host "Process with PID $stalePid is not a running postgres instance. Removing stale postmaster.pid..."
                Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
            } else {
                Write-Host "Active postgres process (PID $stalePid) is already running."
            }
        } else {
            Write-Host "Invalid PID format in postmaster.pid. Cleaning up..."
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Host "Could not read/verify postmaster.pid. Cleaning up..."
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

# Check if service exists
if (!(Get-Service $serviceName -ErrorAction SilentlyContinue)) {
    Write-Host "Service $serviceName not found. Attempting to create it..."
    # Create the service running as NetworkService (Requires Admin)
    sc.exe create $serviceName binPath= $binPath start= auto obj= "NT AUTHORITY\NetworkService"
}

# Try to start the service
try {
    Write-Host "Starting PostgreSQL service..."
    Start-Service $serviceName -ErrorAction Stop
    Write-Host "PostgreSQL service started successfully."
} catch {
    Write-Host "Warning: Could not start service. Falling back to manual startup via pg_ctl..."
    
    # Check if it's already running
    $ps = Get-Process postgres -ErrorAction SilentlyContinue
    if ($ps) {
        Write-Host "PostgreSQL process already appears to be running."
    } else {
        # Start manually (doesn't require admin if user has access to data dir)
        Write-Host "Executing: & `"$pgDir\bin\pg_ctl.exe`" -D `"$pgData`" start"
        & "$pgDir\bin\pg_ctl.exe" -D "$pgData" start
        # Wait a bit for it to initialize
        Start-Sleep -s 2
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL started manually via pg_ctl."
        } else {
            Write-Host "Error: Failed to start PostgreSQL manually. Check logs in $pgData\log"
        }
    }
}
