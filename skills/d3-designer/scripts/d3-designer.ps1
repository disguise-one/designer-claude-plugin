param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "status", "create-blank")]
    [string]$Action,
    [string]$Target,
    [string]$ProjectPath,
    [string]$ProjectName,
    [bool]$Solo = $true,
    [string]$D3Host = "localhost",
    [int]$Port = 80,
    [string]$Scheme = "http",
    [int]$StartTimeout = 120,
    [switch]$DryRun
)

. "$PSScriptRoot\d3-common.ps1"

$baseUrl = "${Scheme}://${D3Host}:${Port}"

switch ($Action) {
    "start" {
        if (-not $Target) {
            throw "-Target is required for 'start'. Available: $(($Installations.Keys | Sort-Object) -join ', ')"
        }
        if (-not $ProjectPath) { throw "-ProjectPath is required for 'start'." }

        $d3Exe = Get-D3ExePath -Target $Target -ExeName "d3.exe"
        if (-not (Test-Path $d3Exe)) {
            throw "d3.exe not found at: $d3Exe"
        }

        # Find running d3.exe + webviewprocess; d3service stays running
        $existing = @()
        foreach ($name in $D3AppProcesses) {
            if (Get-Process -Name $name -ErrorAction SilentlyContinue) { $existing += $name }
        }

        # Build argument list (avoid $args - it's a PowerShell automatic variable)
        $d3Args = @("`"$ProjectPath`"", "-noMessageBox")
        if ($Solo) { $d3Args += "-soloMode" }

        # -DryRun must return before anything stops or starts
        if ($DryRun) {
            if ($existing.Count -gt 0) {
                Write-Host "[DryRun] Would stop existing d3 processes: $($existing -join ', ')"
            }
            Write-Host "[DryRun] Would start: $d3Exe $($d3Args -join ' ')"
            return
        }

        if ($existing.Count -gt 0) {
            Write-Host "WARNING: d3 is running. This action stops it. Unsaved changes in the open project can be lost."
            Write-Host "Stopping existing d3 processes: $($existing -join ', ')..."
            Stop-Processes -Names $D3AppProcesses -BaseUrl $baseUrl -GracefulQuit | Out-Null
        }

        Write-Host "Starting d3 from $Target..."
        Write-Host "  exe: $d3Exe"
        Write-Host "  project: $ProjectPath"

        # Launch d3.exe fully detached from this script's process tree.
        # WMI creates the process via WmiPrvSE.exe, so it won't be killed
        # if the calling script/shell is terminated.
        $argString = $d3Args -join " "
        Start-ProcessDetached -ExePath $d3Exe -Arguments $argString

        Write-Host "Waiting for d3 to be ready (up to ${StartTimeout}s)..."
        $health = Wait-ForDesignerReady -BaseUrl $baseUrl -TimeoutSeconds $StartTimeout

        if ($health -eq "exited") {
            Write-Host ""
            Write-Host "=== d3 FAILED TO START ==="
            Write-Host "  d3.exe exited before becoming ready."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console.txt"
            throw "d3.exe exited before becoming ready. Check log: $env:LOCALAPPDATA\d3\console.txt"
        } elseif ($health) {
            $fps = $health.result[0].status.averageFPS
            try {
                $proj = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/session/status/project" -TimeoutSec 5 -ErrorAction Stop
                $projPath = $proj.result.projectPath
            } catch { $projPath = "(unknown)" }

            Write-Host ""
            Write-Host "=== d3 READY ==="
            Write-Host "  Target:   $Target"
            Write-Host "  Project:  $projPath"
            Write-Host "  FPS:      $fps"
        } else {
            Write-Host ""
            Write-Host "=== d3 NOT READY (timeout) ==="
            Write-Host "  d3.exe is running but health not reporting FPS after ${StartTimeout}s."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console.txt"
        }
    }
    "stop" {
        $d3Running = [bool](Get-Process -Name "d3" -ErrorAction SilentlyContinue)
        if (-not $d3Running) {
            Write-Host "d3 is not running."
            return
        }
        if ($DryRun) {
            Write-Host "[DryRun] Would stop d3"
            return
        }
        $running = Get-RunningInstallation
        if ($running) {
            Write-Host "Stopping d3 (running from: $running)..."
        } else {
            Write-Host "Stopping d3..."
        }
        $clean = Stop-Processes -Names $D3AppProcesses -BaseUrl $baseUrl -GracefulQuit
        if ($clean) {
            Write-Host "d3 stopped."
        }
    }
    "create-blank" {
        if (-not $Target) {
            throw "-Target is required for 'create-blank'. Available: $(($Installations.Keys | Sort-Object) -join ', ')"
        }
        if (-not $ProjectName) { throw "-ProjectName is required for 'create-blank'." }

        # Read project directory from registry
        $regKey = "HKCU:\Software\d3 Technologies\d3 Production Suite"
        $regVal = Get-ItemProperty -Path $regKey -Name "d3 Projects Folder" -ErrorAction SilentlyContinue
        if (-not $regVal) {
            throw "Registry key not found: $regKey\d3 Projects Folder"
        }
        $ProjectDir = $regVal."d3 Projects Folder"
        if (-not (Test-Path $ProjectDir)) {
            throw "Projects folder does not exist: $ProjectDir"
        }

        $inst = $Installations[$Target]
        if (-not $inst) {
            $available = ($Installations.Keys | Sort-Object) -join ", "
            throw "Unknown target '$Target'. Available: $available"
        }

        # Locate blank.zip in the installation
        $blankZip = if ($inst.ExeSubpath) {
            Join-Path $inst.Root (Join-Path $inst.ExeSubpath "blank.zip")
        } else {
            Join-Path $inst.Root "blank.zip"
        }
        if (-not (Test-Path $blankZip)) {
            throw "blank.zip not found at: $blankZip"
        }

        # Create project directory and extract
        $projDir = Join-Path $ProjectDir $ProjectName
        if (Test-Path $projDir) {
            throw "Project directory already exists: $projDir"
        }

        if ($DryRun) {
            Write-Host "[DryRun] Would create: $projDir from $blankZip"
            Write-Host "[DryRun] Would stop a running d3, then start d3 with the new project."
            return
        }

        Write-Host "Creating blank project '$ProjectName'..."
        Write-Host "  source: $blankZip"
        Write-Host "  target: $projDir"

        New-Item -ItemType Directory -Path $projDir -Force | Out-Null
        Expand-Archive -Path $blankZip -DestinationPath $projDir -Force

        # Find the .d3 file
        $d3File = Get-ChildItem -Path $projDir -Filter "*.d3" -Recurse | Select-Object -First 1
        if (-not $d3File) {
            throw "No .d3 file found after extracting blank.zip to $projDir"
        }

        # Rename to match project name if needed
        $expectedName = "$ProjectName.d3"
        if ($d3File.Name -ne $expectedName) {
            $newPath = Join-Path $d3File.DirectoryName $expectedName
            Rename-Item -Path $d3File.FullName -NewName $expectedName
            $d3File = Get-Item $newPath
        }

        $projectPath = $d3File.FullName
        Write-Host "  project: $projectPath"
        Write-Host ""

        # Start d3 with the new project
        $d3Exe = Get-D3ExePath -Target $Target -ExeName "d3.exe"
        if (-not (Test-Path $d3Exe)) {
            throw "d3.exe not found at: $d3Exe"
        }

        # Stop d3.exe + webviewprocess only; leave d3service alone
        $existing = @()
        foreach ($name in $D3AppProcesses) {
            if (Get-Process -Name $name -ErrorAction SilentlyContinue) { $existing += $name }
        }
        if ($existing.Count -gt 0) {
            Write-Host "WARNING: d3 is running. This action stops it. Unsaved changes in the open project can be lost."
            Write-Host "Stopping existing d3 processes: $($existing -join ', ')..."
            Stop-Processes -Names $D3AppProcesses -BaseUrl $baseUrl -GracefulQuit | Out-Null
        }

        $d3Args = @("`"$projectPath`"", "-noMessageBox")
        if ($Solo) { $d3Args += "-soloMode" }

        Write-Host "Starting d3 from $Target..."
        Write-Host "  exe: $d3Exe"
        $argString = $d3Args -join " "
        Start-ProcessDetached -ExePath $d3Exe -Arguments $argString

        Write-Host "Waiting for d3 to be ready (up to ${StartTimeout}s)..."
        $health = Wait-ForDesignerReady -BaseUrl $baseUrl -TimeoutSeconds $StartTimeout

        if ($health -eq "exited") {
            Write-Host ""
            Write-Host "=== d3 FAILED TO START ==="
            Write-Host "  d3.exe exited before becoming ready."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console.txt"
            throw "d3.exe exited before becoming ready. Check log: $env:LOCALAPPDATA\d3\console.txt"
        } elseif ($health) {
            $fps = $health.result[0].status.averageFPS
            Write-Host ""
            Write-Host "=== d3 READY ==="
            Write-Host "  Target:   $Target"
            Write-Host "  Project:  $projectPath"
            Write-Host "  FPS:      $fps"
        } else {
            Write-Host ""
            Write-Host "=== d3 NOT READY (timeout) ==="
            Write-Host "  d3.exe is running but health not reporting FPS after ${StartTimeout}s."
            Write-Host "  Check log: $env:LOCALAPPDATA\d3\console.txt"
        }
    }
    "status" {
        $isLocal = ($D3Host -eq "localhost" -or $D3Host -eq "127.0.0.1")

        if ($isLocal) {
            # Local: process check avoids network calls when nothing is running
            $running = Get-RunningInstallation
            if (-not $running) {
                $orphans = Get-AnyD3Processes
                if ($orphans.Count -gt 0) {
                    Write-Host "d3 installation unknown, but processes found: $($orphans -join ', ')"
                } else {
                    Write-Host "d3 is not running."
                }
                return
            }
        } else {
            # Remote: can't check processes — use TCP reachability first
            $reachable = Test-NetConnection -ComputerName $D3Host -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
            if (-not $reachable) {
                Write-Host "d3 is not running on ${D3Host}:${Port} (port unreachable)."
                return
            }
        }

        Write-Host "=== d3 STATUS ==="
        if ($isLocal) { Write-Host "  Installation: $running" }
        else           { Write-Host "  Host:         ${D3Host}:${Port}" }

        # Health endpoint requires d3.exe with an open project
        try {
            $health = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/session/status/health" -TimeoutSec 5 -ErrorAction Stop
            $status = $health.result[0].status
            Write-Host "  d3.exe:   running"
            Write-Host "  FPS:      $($status.averageFPS)"
            foreach ($state in $status.states) {
                Write-Host "  $($state.name): $($state.detail) ($($state.severity))"
            }
        } catch {
            if ($_.ToString() -match "502") {
                Write-Host "  d3: not running"
            } else {
                Write-Host "  d3: not responding ($($_.Exception.GetType().Name))"
            }
            return
        }

        # Project (only reached if health succeeded)
        try {
            $proj = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/session/status/project" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "  Project:  $($proj.result.projectPath)"
        } catch {}
    }
}
