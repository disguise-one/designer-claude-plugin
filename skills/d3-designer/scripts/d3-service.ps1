param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "switch", "status", "which")]
    [string]$Action,
    [string]$Target,
    [string]$D3Host = "localhost",
    [int]$Port = 80,
    [string]$Scheme = "http",
    [int]$StartTimeout = 30,
    [switch]$DryRun
)

. "$PSScriptRoot\d3-common.ps1"

$baseUrl = "${Scheme}://${D3Host}:${Port}"

switch ($Action) {
    "which" {
        $running = Get-RunningInstallation
        if (-not $running) {
            $orphans = Get-AnyD3Processes
            if ($orphans.Count -gt 0) {
                Write-Host "No d3 installation detected, but orphaned processes found: $($orphans -join ', ')"
            } else {
                Write-Host "d3service is not running"
            }
        } else {
            Write-Host "d3service is running from: $running"
        }
    }
    "status" {
        $reachable = Test-NetConnection -ComputerName $D3Host -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
        if (-not $reachable) {
            throw "d3service not reachable on ${D3Host}:${Port}"
        }
        Write-Host "Connected to ${D3Host}:${Port}"
        try {
            $result = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/session/status/health"
            $result | ConvertTo-Json -Depth 10
        } catch {
            if ($_.ToString() -match "502") {
                Write-Host "d3service not running (502)"
            } else {
                Write-Host "Health endpoint unavailable: $_"
            }
        }
    }
    "start" {
        if (-not $Target) {
            throw "-Target is required for 'start'. Available: $(($Installations.Keys | Sort-Object) -join ', ')"
        }
        $running = Get-RunningInstallation
        if ($running) {
            throw "d3service is already running from: $running. Stop it first or use 'switch'."
        }

        $exePath = Get-D3ExePath -Target $Target -ExeName "d3service.exe"
        if (-not (Test-Path $exePath)) {
            throw "d3service.exe not found at: $exePath"
        }
        if ($DryRun) {
            Write-Host "[DryRun] Would start: $exePath"
            return
        }

        # Clean up any orphaned service processes from a previous session
        $orphans = @()
        foreach ($name in $D3ServiceProcesses) {
            if (Get-Process -Name $name -ErrorAction SilentlyContinue) { $orphans += $name }
        }
        if ($orphans.Count -gt 0) {
            Write-Host "Cleaning up orphaned processes: $($orphans -join ', ')..."
            Stop-Processes -Names $D3ServiceProcesses | Out-Null
        }

        Write-Host "Starting d3service from $Target..."
        Write-Host "  exe: $exePath"

        # Launch d3service.exe fully detached via WMI so it survives
        # if the calling script/shell is terminated.
        Start-ProcessDetached -ExePath $exePath

        Write-Host "Waiting for service API (up to ${StartTimeout}s)..."
        $result = Wait-ForServiceApi -BaseUrl $baseUrl -TimeoutSeconds $StartTimeout

        if ($result -eq "exited") {
            Write-Host ""
            Write-Host "=== d3service FAILED TO START ==="
            Write-Host "  d3service.exe exited before the API became reachable."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console_d3service.txt"
            throw "d3service.exe exited before the API became reachable. Check log: $env:LOCALAPPDATA\d3\console_d3service.txt"
        } elseif ($result -eq "ready") {
            Write-Host ""
            Write-Host "=== d3service READY ==="
            Write-Host "  Target: $Target"
        } else {
            Write-Host ""
            Write-Host "=== d3service NOT READY (timeout) ==="
            Write-Host "  d3service.exe is running but API not responding after ${StartTimeout}s."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console_d3service.txt"
        }
    }
    "stop" {
        $serviceRunning = [bool](Get-Process -Name "d3service" -ErrorAction SilentlyContinue)
        if (-not $serviceRunning) {
            Write-Host "d3service is not running."
            return
        }
        if ($DryRun) {
            Write-Host "[DryRun] Would stop d3service"
            return
        }
        $running = Get-RunningInstallation
        if ($running) {
            Write-Host "Stopping d3service (running from: $running)..."
        } else {
            Write-Host "Stopping d3service..."
        }
        $clean = Stop-Processes -Names $D3ServiceProcesses
        if ($clean) {
            Write-Host "d3service stopped."
        }
    }
    "switch" {
        if (-not $Target) {
            throw "-Target is required for 'switch'. Available: $(($Installations.Keys | Sort-Object) -join ', ')"
        }
        $running = Get-RunningInstallation
        if ($running -eq $Target) {
            Write-Host "d3service is already running from $Target."
            return
        }
        $exePath = Get-D3ExePath -Target $Target -ExeName "d3service.exe"
        if (-not (Test-Path $exePath)) {
            throw "d3service.exe not found at: $exePath"
        }
        if ($DryRun) {
            Write-Host "[DryRun] Would switch from $running to $Target"
            return
        }
        Write-Host "Switching from $running to $Target..."

        # Stop d3service + nginx
        Stop-Processes -Names $D3ServiceProcesses | Out-Null

        # Launch d3service.exe fully detached via WMI
        Start-ProcessDetached -ExePath $exePath

        Write-Host "Waiting for service API (up to ${StartTimeout}s)..."
        $result = Wait-ForServiceApi -BaseUrl $baseUrl -TimeoutSeconds $StartTimeout

        if ($result -eq "exited") {
            Write-Host ""
            Write-Host "=== SWITCH FAILED ==="
            Write-Host "  d3service.exe exited before the API became reachable."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console_d3service.txt"
            throw "Switch failed: d3service.exe exited before the API became reachable. Check log: $env:LOCALAPPDATA\d3\console_d3service.txt"
        } elseif ($result -eq "ready") {
            Write-Host "Switched to $Target successfully."
        } else {
            Write-Host ""
            Write-Host "=== SWITCH INCOMPLETE (timeout) ==="
            Write-Host "  d3service.exe is running but API not responding after ${StartTimeout}s."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console_d3service.txt"
        }
    }
}
