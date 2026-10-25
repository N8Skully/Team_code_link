# Starts a Cloudflare quick tunnel to the local room and writes its public address.
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$urlFile = Join-Path $env:TEMP "team-code-link-tunnel.url"
$pidFile = Join-Path $env:TEMP "team-code-link-tunnel.pid"
$outLog = Join-Path $env:TEMP "team-code-link-tunnel.out.log"
$errLog = Join-Path $env:TEMP "team-code-link-tunnel.err.log"

function Stop-PreviousTunnel {
    if (-not (Test-Path $pidFile)) { return }
    $old = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($old -match '^\d+$') {
        Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

function Find-Cloudflared {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:ProgramFiles "cloudflared\cloudflared.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "cloudflared\cloudflared.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\cloudflared.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    $packages = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $packages) {
        $found = Get-ChildItem -Path $packages -Filter cloudflared.exe -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

function Install-Cloudflared {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        [Console]::Error.WriteLine("Cloudflare Tunnel is not installed, and winget is not available.")
        [Console]::Error.WriteLine("Install cloudflared from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ and run launch.bat again.")
        exit 1
    }
    Write-Host "Installing Cloudflare Tunnel. Windows may ask you to approve this once."
    & winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) {
        & winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements
    }
    if ($LASTEXITCODE -ne 0) {
        [Console]::Error.WriteLine("Cloudflare Tunnel did not install. Approve the Windows prompt, then run launch.bat again.")
        exit 1
    }
}

function Read-SharedText([string]$Path) {
    if (-not (Test-Path $Path)) { return "" }
    $stream = $null
    $reader = $null
    try {
        $stream = [System.IO.File]::Open($Path, "Open", "Read", "ReadWrite")
        $reader = New-Object System.IO.StreamReader($stream)
        return $reader.ReadToEnd()
    } catch {
        return ""
    } finally {
        if ($reader) { $reader.Dispose() }
        elseif ($stream) { $stream.Dispose() }
    }
}

Stop-PreviousTunnel
Remove-Item $urlFile, $outLog, $errLog -Force -ErrorAction SilentlyContinue

$cloudflared = Find-Cloudflared
if (-not $cloudflared) {
    Install-Cloudflared
    $cloudflared = Find-Cloudflared
}
if (-not $cloudflared) {
    [Console]::Error.WriteLine("Cloudflare Tunnel installed, but this window cannot find cloudflared.exe yet.")
    [Console]::Error.WriteLine("Close this window and double-click launch.bat again.")
    exit 1
}

Write-Host "Opening an internet link to this room..."
$proc = Start-Process -FilePath $cloudflared -ArgumentList @(
    "tunnel", "--url", "http://127.0.0.1:$Port", "--protocol", "http2", "--no-autoupdate"
) -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru -WindowStyle Hidden
Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii

$pattern = [regex]"https://[a-z0-9-]+\.trycloudflare\.com"
for ($i = 0; $i -lt 60; $i++) {
    foreach ($file in @($outLog, $errLog)) {
        $text = Read-SharedText $file
        $found = $pattern.Matches($text)
        if ($found.Count -gt 0) {
            $url = $found[$found.Count - 1].Value
            Set-Content -Path $urlFile -Value $url -Encoding ascii
            Write-Host "Tunnel is up. Send the share link printed below. It changes each time you start this window."
            exit 0
        }
    }
    if ($proc.HasExited) { break }
    Start-Sleep -Seconds 1
}

[Console]::Error.WriteLine("The tunnel did not return a public address.")
[Console]::Error.WriteLine("Details:")
$details = Read-SharedText $errLog
if ($details) {
    $lines = $details -split "`r?`n"
    $start = [Math]::Max(0, $lines.Length - 30)
    $lines[$start..($lines.Length - 1)] | ForEach-Object { [Console]::Error.WriteLine($_) }
}
Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
exit 1
