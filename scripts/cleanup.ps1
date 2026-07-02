# Cleanup script for common regenerable artifacts
# Run from repository root

$paths = @(
    "node_modules",
    "dist_electron",
    "dist",
    "build",
    "ai_machine.zip",
    "backups/code_temp",
    ".venv",
    "ai_machine/dist",
    "ai_machine/build",
    "assets/models"
)

foreach ($p in $paths) {
    Write-Host "Removing: $p"
    try {
        if (Test-Path $p) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction Stop }
    } catch {
        Write-Warning "Failed to remove $p : $_"
    }
}

Write-Host "Cleanup complete. Consider running 'git gc' to reclaim space after large file removals."