param(
    [Parameter(Mandatory = $true)]
    [string]$Mappings,
    # Must be a folder that the d3 host can write and this script can read.
    # The default is a folder in the temp folder, which works when d3 runs on this machine.
    [string]$OutputDir = (Join-Path ([System.IO.Path]::GetTempPath()) "d3-captures"),
    [string]$D3Host = "localhost",
    [int]$Port = 80,
    [string]$Scheme = "http",
    [int]$WaitMs = 2000
)

. "$PSScriptRoot/d3-python-common.ps1"

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$pythonUrl = "{0}://{1}:{2}/api/session/python/execute" -f $Scheme, $D3Host, $Port
$transportBaseUrl = "{0}://{1}:{2}/api/session/transport" -f $Scheme, $D3Host, $Port

function Invoke-D3Python {
    param([string]$Script, [string]$Module = "mcp_helpers")
    $bodyObject = @{ moduleName = $Module; script = $Script }
    $body = ConvertTo-JsonCompat -Object $bodyObject
    try {
        $response = Invoke-RestMethod -Method Post -Uri $pythonUrl -ContentType "application/json" -Body $body
    } catch {
        $errResp = $_.ErrorDetails.Message
        if ($errResp) {
            Write-Host "# Error"
            Write-Host '```'
            Write-Host $errResp
            Write-Host '```'
            return $null
        } else {
            Write-Host "# Error"
            Write-Host '```'
            Write-Host $_.Exception.Message
            Write-Host '```'
            return $null
        }
    }
    # Check for Python errors
    $status = if ($response.status) { $response.status } elseif ($response.result -and $response.result.status) { $response.result.status } else { $null }
    if ($status -and $status.code -and $status.code -ne "OK") {
        Write-Host (Format-D3Response $response)
        return $null
    }
    return $response
}

function Get-ReturnValue {
    param($Response)
    if ($null -eq $Response) { return $null }
    $rv = if ($Response.returnValue -ne $null) { $Response.returnValue } elseif ($Response.result -and $Response.result.returnValue -ne $null) { $Response.result.returnValue } else { $null }
    return $rv
}

function Invoke-GotoTrack {
    param([string]$TrackName)
    # Find the transport name first
    $listUrl = "$transportBaseUrl/transports"
    $transports = Invoke-RestMethod -Method Get -Uri $listUrl
    $transportName = $transports.transports[0].name
    $postBody = @{
        transports = @(
            @{
                transport = @{ name = $transportName }
                track = @{ name = $TrackName }
            }
        )
    } | ConvertTo-Json -Depth 10 -Compress
    try {
        Invoke-RestMethod -Method Post -Uri "$transportBaseUrl/gototrack" -ContentType "application/json" -Body $postBody | Out-Null
    } catch {
        Write-Host "  Warning: gototrack failed: $($_.Exception.Message)"
    }
}

function Invoke-GotoBeat {
    param([float]$Beat)
    $transports = Invoke-RestMethod -Method Get -Uri "$transportBaseUrl/transports"
    $transportName = $transports.transports[0].name
    $postBody = @{
        transports = @(
            @{
                transport = @{ name = $transportName }
                time = $Beat
            }
        )
    } | ConvertTo-Json -Depth 10 -Compress
    try {
        Invoke-RestMethod -Method Post -Uri "$transportBaseUrl/gototime" -ContentType "application/json" -Body $postBody | Out-Null
    } catch {
        Write-Host "  Warning: gototime failed: $($_.Exception.Message)"
    }
}

function Wait-ForCapture {
    param([string]$Dir, [datetime]$After)
    Start-Sleep -Milliseconds $WaitMs
    $captures = Get-ChildItem -Path $Dir -Filter "screen_*.png" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt $After } |
        Sort-Object LastWriteTime -Descending
    if ($captures -and $captures.Count -gt 0) {
        return $captures[0].FullName
    }
    # Retry once with extra wait
    Start-Sleep -Milliseconds $WaitMs
    $captures = Get-ChildItem -Path $Dir -Filter "screen_*.png" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt $After } |
        Sort-Object LastWriteTime -Descending
    if ($captures -and $captures.Count -gt 0) {
        return $captures[0].FullName
    }
    return $null
}

# Parse mappings JSON
try {
    $mappingData = $Mappings | ConvertFrom-Json
} catch {
    Write-Host "# Error: Invalid Mappings JSON"
    Write-Host '```'
    Write-Host $_.Exception.Message
    Write-Host '```'
    exit 1
}

$mappingList = $mappingData.mappings
if (-not $mappingList -or $mappingList.Count -eq 0) {
    Write-Host "# Error: No mappings provided"
    Write-Host 'Expected: -Mappings ''{"mappings": [{"name": "Centre", "path": "objects/directprojection/centre.apx"}]}'''
    exit 1
}

$outputDirFwd = $OutputDir -replace '\\', '/'
$results = @()

# Step 1: Create lineup track
Write-Host "Creating lineup track..."
$resp = Invoke-D3Python -Script "return create_lineup_track()"
$rv = Get-ReturnValue -Response $resp
if ($null -eq $rv) {
    Write-Host "# Error: Failed to create lineup track"
    Write-Host (Format-D3Response $resp)
    exit 1
}
if ($rv.error) {
    Write-Host "# Error: $($rv.error)"
    exit 1
}

$screenInfo = $rv

# Step 2: Navigate to lineup track section 0 and capture screen check
Write-Host "Capturing screen check (section 0)..."
Invoke-GotoTrack -TrackName "mcp_lineup"
Start-Sleep -Milliseconds 500

$beforeCapture = Get-Date
$resp = Invoke-D3Python -Script "return capture_stage('$outputDirFwd')"
$screenCheckImage = Wait-ForCapture -Dir $OutputDir -After $beforeCapture

$results += @{
    section = "Screen Check"
    image = if ($screenCheckImage) { $screenCheckImage } else { "capture_failed" }
    screens = $screenInfo.screens
}

# Step 3: Check out each mapping
foreach ($mapping in $mappingList) {
    $name = $mapping.name
    $path = $mapping.path
    Write-Host "Checking out mapping: $name ($path)..."

    # Escape single quotes in path for Python string
    $escapedPath = $path -replace "'", "\\'"

    # checkout_mapping creates the layer, jumps to beat 30
    $resp = Invoke-D3Python -Script "return checkout_mapping('$escapedPath')"
    $rv = Get-ReturnValue -Response $resp
    if ($null -eq $rv -or $rv.error) {
        $errMsg = if ($rv -and $rv.error) { $rv.error } else { "checkout_mapping failed" }
        Write-Host "  Warning: $errMsg"
        $results += @{
            section = $name
            image = "error: $errMsg"
            projection = $path
        }
        continue
    }

    # Wait for render, then capture in a separate Python call
    Start-Sleep -Milliseconds 500
    $beforeCapture = Get-Date
    $resp = Invoke-D3Python -Script "return capture_stage('$outputDirFwd')"
    $captureImage = Wait-ForCapture -Dir $OutputDir -After $beforeCapture

    $results += @{
        section = $name
        image = if ($captureImage) { $captureImage } else { "capture_failed" }
        projection = $path
        colour = $rv.colour
    }
}

# Step 4: Cleanup
Write-Host "Cleaning up checkout layers..."
Invoke-D3Python -Script "return cleanup_checkout()" | Out-Null

# Step 5: Navigate back to section 0
Invoke-GotoTrack -TrackName "mcp_lineup"

# Output results as JSON
Write-Host ""
Write-Host "# Lineup Capture Results"
Write-Host '```json'
Write-Host ($results | ConvertTo-Json -Depth 10)
Write-Host '```'
Write-Host ""
Write-Host "Use the MCP client's image-reading tool on each image path to visually verify mapping coverage."
