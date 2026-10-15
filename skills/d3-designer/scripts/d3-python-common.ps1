function ConvertTo-JsonCompat {
    param([Parameter(Mandatory = $true)]$Object)
    if (Get-Command -Name ConvertTo-Json -ErrorAction SilentlyContinue) {
        return $Object | ConvertTo-Json -Compress
    }
    Add-Type -AssemblyName System.Web.Extensions
    $serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
    return $serializer.Serialize($Object)
}

function Get-FileText {
    param([Parameter(Mandatory = $true)][string]$Path)
    [System.IO.File]::ReadAllText($Path)
}

# Format response as readable markdown
function Format-D3Response {
    param($R)
    $lines = [System.Collections.Generic.List[string]]::new()

    # Status
    $status = if ($R.status) { $R.status } elseif ($R.result -and $R.result.status) { $R.result.status } else { $null }
    if ($status) {
        $code = if ($status.code) { $status.code } else { $status }
        $lines.Add("# Status: $code")
        if ($status.message) { $lines.Add($status.message) }
        if ($status.details) { $lines.Add($status.details) }
    }

    # pythonLog
    $pyLog = if ($R.pythonLog) { $R.pythonLog } elseif ($R.result) { $R.result.pythonLog } else { $null }
    if ($pyLog -and $pyLog.Trim()) {
        $lines.Add("")
        $lines.Add("## pythonLog")
        $lines.Add('```')
        $lines.Add($pyLog.TrimEnd())
        $lines.Add('```')
    }

    # returnValue — pretty-print as JSON if possible
    $rv = if ($R.returnValue -ne $null) { $R.returnValue } elseif ($R.result -and $R.result.returnValue -ne $null) { $R.result.returnValue } else { $null }
    if ($rv -ne $null) {
        # If Invoke-RestMethod already deserialized it, re-serialize for display
        if ($rv -is [PSCustomObject] -or $rv -is [System.Collections.IDictionary] -or $rv -is [System.Array]) {
            $pretty = $rv | ConvertTo-Json -Depth 10
            $lang = "json"
        } elseif ("$rv".Trim()) {
            # It's a string — try to parse as JSON for pretty-printing
            $pretty = "$rv"
            $lang = ""
            try {
                $parsed = "$rv" | ConvertFrom-Json
                $pretty = $parsed | ConvertTo-Json -Depth 10
                $lang = "json"
            } catch {}
        } else {
            $pretty = $null
        }
        if ($pretty) {
            $lines.Add("")
            $lines.Add("## returnValue")
            $lines.Add('```' + $lang)
            $lines.Add($pretty.TrimEnd())
            $lines.Add('```')
        }
    }

    # d3Log (last — noisiest, often contains unrelated output)
    $d3Log = if ($R.d3Log) { $R.d3Log } elseif ($R.result) { $R.result.d3Log } else { $null }
    if ($d3Log -and $d3Log.Trim()) {
        $lines.Add("")
        $lines.Add("## d3Log")
        $lines.Add('```')
        $lines.Add($d3Log.TrimEnd())
        $lines.Add('```')
    }

    return ($lines -join "`n")
}
