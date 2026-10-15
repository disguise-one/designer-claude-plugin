# d3-common.ps1 — shared module for d3 skill scripts
# Dot-source this at the top of each script: . "$PSScriptRoot\d3-common.ps1"

# Process groups: d3-designer stops $D3AppProcesses; d3-service stops $D3ServiceProcesses
$D3AppProcesses = @("d3", "webviewprocess")
$D3ServiceProcesses = @("d3service", "nginx")

# --- Configuration -----------------------------------------------------------

# Targets (named d3 installations) come from three sources. A later source
# adds targets to the earlier ones. All sources are optional.
#   1. "release": the Program Files install, found automatically.
#   2. "env": the folder in the D3_INSTALL_ROOT environment variable.
#      D3_EXE_SUBPATH is the optional folder of the executables below it.
#   3. Names from an optional JSON file. The file is the path in the
#      D3_CONFIG_PATH environment variable, or d3-config.json next to this
#      script. config.example.json shows the format.
function Load-D3Config {
    $installations = @{}

    # Source 1: Release install (auto-detected from Program Files)
    $releaseRoot = "$env:ProgramFiles\d3 Production Suite"
    $releaseExeDir = Join-Path $releaseRoot "build\msvc"
    if (Test-Path $releaseExeDir) {
        $installations["release"] = @{
            Root       = $releaseRoot
            ExeSubpath = "build\msvc"
        }
    }

    # Source 2: One install from environment variables
    if ($env:D3_INSTALL_ROOT) {
        $installations["env"] = @{
            Root       = [Environment]::ExpandEnvironmentVariables($env:D3_INSTALL_ROOT)
            ExeSubpath = if ($env:D3_EXE_SUBPATH) { $env:D3_EXE_SUBPATH } else { "" }
        }
    }

    # Source 3: Named installations from a JSON file
    $configPath = if ($env:D3_CONFIG_PATH) { $env:D3_CONFIG_PATH }
                  else { Join-Path $PSScriptRoot "d3-config.json" }
    if (Test-Path $configPath) {
        $raw = Get-Content $configPath -Raw | ConvertFrom-Json

        # Hostname check (warn-only)
        if ($raw.hostname -and $raw.hostname -ne $env:COMPUTERNAME) {
            Write-Host "WARNING: d3-config.json is for host '$($raw.hostname)' but this is '$env:COMPUTERNAME'. Paths may be wrong."
        }

        foreach ($prop in $raw.installations.PSObject.Properties) {
            $name = $prop.Name
            if ($name -eq "release") {
                Write-Host "WARNING: 'release' is reserved for the Program Files install. Ignoring config entry."
                continue
            }
            $inst = $prop.Value
            $installations[$name] = @{
                Root       = [Environment]::ExpandEnvironmentVariables($inst.root)
                ExeSubpath = if ($inst.PSObject.Properties["exeSubpath"] -and $inst.exeSubpath) { $inst.exeSubpath } else { "" }
            }
        }
    }

    if ($installations.Count -eq 0) {
        throw "No d3 installations found. Install d3 to Program Files, set D3_INSTALL_ROOT, or create a d3-config.json (see config.example.json in this folder)."
    }

    return $installations
}

# Load config at dot-source time so all scripts have $Installations available
$Installations = Load-D3Config

# --- Path helpers ------------------------------------------------------------

function Get-D3ExePath {
    param(
        [string]$Target,
        [string]$ExeName = "d3.exe"
    )
    if (-not $Installations.ContainsKey($Target)) {
        $available = ($Installations.Keys | Sort-Object) -join ", "
        throw "Unknown target '$Target'. Available: $available"
    }
    $inst = $Installations[$Target]
    if ($inst.ExeSubpath) {
        Join-Path $inst.Root (Join-Path $inst.ExeSubpath $ExeName)
    } else {
        Join-Path $inst.Root $ExeName
    }
}

# --- Process detection -------------------------------------------------------

function Get-RunningInstallation {
    foreach ($name in @("d3", "d3service")) {
        $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
        if ($procs) {
            foreach ($proc in $procs) {
                $path = $proc.Path
                # Check longest roots first, so a root does not match a longer root that starts with the same text
                $sorted = $Installations.GetEnumerator() | Sort-Object { $_.Value.Root.Length } -Descending
                foreach ($entry in $sorted) {
                    if ($path -like "$($entry.Value.Root)\*") {
                        return $entry.Key
                    }
                }
            }
        }
    }
    return $null
}

function Get-AnyD3Processes {
    $found = @()
    foreach ($name in ($D3AppProcesses + $D3ServiceProcesses)) {
        if (Get-Process -Name $name -ErrorAction SilentlyContinue) { $found += $name }
    }
    return $found
}

# --- Process lifecycle -------------------------------------------------------

function Stop-Processes {
    param(
        [Parameter(Mandatory)]
        [string[]]$Names,
        [string]$BaseUrl = "",
        [switch]$GracefulQuit
    )

    # Graceful quit via API (best-effort, only for d3 app shutdown)
    if ($GracefulQuit -and $BaseUrl) {
        try {
            Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/service/project/forcequitlocalproject" `
                -ContentType "application/json" -Body "{}" -TimeoutSec 5 -ErrorAction SilentlyContinue | Out-Null
            Start-Sleep -Seconds 2
        } catch {}
    }

    # Force kill
    foreach ($name in $Names) {
        Stop-Process -Name $name -Force -ErrorAction SilentlyContinue
    }

    # Wait for exit
    for ($i = 0; $i -lt 10; $i++) {
        $alive = @()
        foreach ($name in $Names) {
            if (Get-Process -Name $name -ErrorAction SilentlyContinue) { $alive += $name }
        }
        if ($alive.Count -eq 0) { return $true }
        Start-Sleep -Seconds 1
    }
    $alive = @()
    foreach ($name in $Names) {
        if (Get-Process -Name $name -ErrorAction SilentlyContinue) { $alive += $name }
    }
    if ($alive.Count -gt 0) {
        Write-Host "WARNING: still running after 10s: $($alive -join ', ')"
        return $false
    }
    return $true
}

# --- Process launching -------------------------------------------------------

function Start-ProcessDetached {
    param(
        [Parameter(Mandatory)]
        [string]$ExePath,
        [string]$Arguments = ""
    )
    $cmd = "`"$ExePath`""
    if ($Arguments) { $cmd += " $Arguments" }
    $wmiResult = ([wmiclass]"Win32_Process").Create($cmd)
    if ($wmiResult.ReturnValue -ne 0) {
        $exeName = Split-Path $ExePath -Leaf
        throw "Failed to launch $exeName (WMI error code: $($wmiResult.ReturnValue))"
    }
}

# --- Readiness polling -------------------------------------------------------

# Poll health endpoint until averageFPS > 0, bail if d3.exe exits
function Wait-ForDesignerReady {
    param(
        [string]$BaseUrl,
        [int]$TimeoutSeconds = 120
    )
    $url = "$BaseUrl/api/session/status/health"
    $lastStatus = ""
    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        # Check d3.exe is still alive
        if (-not (Get-Process -Name "d3" -ErrorAction SilentlyContinue)) {
            Write-Host "  [${i}s] d3.exe exited"
            return "exited"
        }
        try {
            # Use WebClient instead of Invoke-RestMethod to avoid .NET
            # ServicePointManager caching failed connections and refusing
            # to reconnect after d3service comes up.
            $wc = New-Object System.Net.WebClient
            $json = $wc.DownloadString($url)
            $wc.Dispose()
            $result = $json | ConvertFrom-Json
            $fps = $result.result[0].status.averageFPS
            if ($fps -gt 0) {
                Write-Host "  [${i}s] FPS=$fps - ready"
                return $result
            }
            $newStatus = "connected, FPS=$fps"
        } catch {
            $newStatus = "$($_.Exception.GetType().Name)"
        }
        # Print status changes to show progress
        if ($newStatus -ne $lastStatus) {
            Write-Host "  [${i}s] $newStatus"
            $lastStatus = $newStatus
        }
        Start-Sleep -Seconds 1
    }
    return $null
}

# Poll the d3service API until it responds, bail if process exits
function Wait-ForServiceApi {
    param(
        [string]$BaseUrl,
        [int]$TimeoutSeconds = 30
    )
    $url = "$BaseUrl/api/service/system/osinfo"
    $lastStatus = ""
    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        # Check d3service.exe is still alive
        if (-not (Get-Process -Name "d3service" -ErrorAction SilentlyContinue)) {
            Write-Host "  [${i}s] d3service.exe exited"
            return "exited"
        }
        try {
            # Use WebClient instead of Invoke-RestMethod to avoid .NET
            # ServicePointManager caching failed connections and refusing
            # to reconnect after d3service comes up.
            $wc = New-Object System.Net.WebClient
            $wc.DownloadString($url) | Out-Null
            $wc.Dispose()
            Write-Host "  [${i}s] API responding - ready"
            return "ready"
        } catch {
            $newStatus = "$($_.Exception.GetType().Name)"
        }
        if ($newStatus -ne $lastStatus) {
            Write-Host "  [${i}s] $newStatus"
            $lastStatus = $newStatus
        }
        Start-Sleep -Seconds 1
    }
    return $null
}
