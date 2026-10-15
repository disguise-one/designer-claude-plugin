# -OutputDir must be a folder that the d3 host can write and this script can read.
# The default is a folder in the temp folder, which works when d3 runs on this machine.
param(
    [string]$OutputDir = (Join-Path ([System.IO.Path]::GetTempPath()) "d3-captures"),
    [int]$Width = 1280,
    [int]$Height = 720,
    [float]$FOV = 60.0,
    [string]$D3Host = "localhost",
    [int]$Port = 80,
    [string]$Scheme = "http",
    [int]$WaitMs = 3000
)

. "$PSScriptRoot/d3-python-common.ps1"

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Call capture_stage via mcp_helpers module
$script = "return capture_stage('$($OutputDir -replace '\\', '/')', $Width, $Height, $FOV)"
$bodyObject = @{ moduleName = "mcp_helpers"; script = $script }
$body = ConvertTo-JsonCompat -Object $bodyObject
$url = "{0}://{1}:{2}/api/session/python/execute" -f $Scheme, $D3Host, $Port

try {
    $response = Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $body
} catch {
    $errResp = $_.ErrorDetails.Message
    if ($errResp) {
        Write-Host "# Error executing capture"
        Write-Host '```'
        Write-Host $errResp
        Write-Host '```'
        exit 1
    } else {
        Write-Host "# Error"
        Write-Host '```'
        Write-Host $_.Exception.Message
        Write-Host '```'
        exit 1
    }
}

# Check for Python errors
$status = if ($response.status) { $response.status } elseif ($response.result -and $response.result.status) { $response.result.status } else { $null }
if ($status -and $status.code -and $status.code -ne "OK") {
    Write-Host (Format-D3Response $response)
    exit 1
}

# Wait for the capture file to appear
Write-Host "Waiting for capture..."
Start-Sleep -Milliseconds $WaitMs

# Find the most recent PNG in output dir matching screen_*
$captures = Get-ChildItem -Path $OutputDir -Filter "screen_*.png" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if (-not $captures -or $captures.Count -eq 0) {
    Write-Host "# Warning: No capture file found in $OutputDir after ${WaitMs}ms"
    Write-Host "The capture may need more time, or SaveFrameSystem may not have rendered yet."
    Write-Host (Format-D3Response $response)
    exit 1
}

$capturePath = $captures[0].FullName
Write-Host "Captured: $capturePath"
Write-Host ""
Write-Host "Use the MCP client's image-reading tool on this image to visually verify the stage layout:"
Write-Host $capturePath
