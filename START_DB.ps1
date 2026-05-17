$serviceName = "postgresql-x64-18"
$pgDir = "C:\Program Files\PostgreSQL\18"
$binPath = "`"$pgDir\bin\postgres.exe`" -D `"$pgDir\data`""
$pgCtl = "`"$pgDir\bin\pg_ctl.exe`""
$pgData = "`"$pgDir\data`""

Write-Host "Attempting to manage PostgreSQL service..."

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
            # exit 1 # Don't exit here so we can see what happens in the caller
        }
    }
}
