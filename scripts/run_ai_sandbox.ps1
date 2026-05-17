param(
    [string] $Sandbox,
    [string] $LogDir,
    [string] $Config,
    [string] $Method,
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

function ConvertTo-SingleQuotedLiteral {
    param([string] $Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Resolve-MethodFromPointer {
    param([string] $RepoRoot)

    $Pointer = Join-Path $RepoRoot "jingu-method-source.txt"
    if (-not (Test-Path -LiteralPath $Pointer)) {
        return $null
    }

    $Target = Get-Content -LiteralPath $Pointer -Encoding UTF8 |
        Where-Object { $_.Trim() -and -not $_.Trim().StartsWith("#") } |
        Select-Object -First 1
    if (-not $Target) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($Target)) {
        return $Target
    }
    return Join-Path $RepoRoot $Target
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not $Sandbox) {
    $Sandbox = Join-Path $env:TEMP ("jingu-ai-sandbox-" + [guid]::NewGuid().ToString("N"))
}
if (-not $LogDir) {
    $LogDir = Join-Path $RepoRoot "local-ai-logs"
}
if (-not $Method) {
    $Method = Resolve-MethodFromPointer $RepoRoot
}

$RepoLiteral = ConvertTo-SingleQuotedLiteral $RepoRoot
$SandboxLiteral = ConvertTo-SingleQuotedLiteral $Sandbox
$LogDirLiteral = ConvertTo-SingleQuotedLiteral $LogDir
$ReadablePointer = Join-Path $LogDir "latest-readable-log.txt"

$ConfigArgs = ""
if ($Config) {
    $ConfigLiteral = ConvertTo-SingleQuotedLiteral $Config
    $ConfigArgs = " --config $ConfigLiteral"
}

$MethodArgs = ""
if ($Method) {
    $MethodLiteral = ConvertTo-SingleQuotedLiteral $Method
    $MethodArgs = " --method $MethodLiteral"
}

$Utf8Setup = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; `$OutputEncoding = [System.Text.Encoding]::UTF8; `$env:PYTHONUTF8 = '1';"
$MonitorCommand = "& { $Utf8Setup Set-Location -LiteralPath $RepoLiteral; python -m jingu.cli ai monitor --sandbox $SandboxLiteral --log-dir $LogDirLiteral --wait-seconds 3600 }"
$ChatCommand = "& { $Utf8Setup Set-Location -LiteralPath $RepoLiteral; python -m jingu.cli ai chat --sandbox $SandboxLiteral --log-dir $LogDirLiteral$ConfigArgs$MethodArgs }"

if ($DryRun) {
    Write-Host "Monitor command: $MonitorCommand"
    Write-Host "Chat command: $ChatCommand"
    Write-Host "Sandbox: $Sandbox"
    Write-Host "Logs: $LogDir"
    Write-Host "Readable pointer: $ReadablePointer"
    Write-Host "Method: $Method"
    exit 0
}

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $MonitorCommand)
Start-Sleep -Milliseconds 500
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $ChatCommand)

Write-Host "Started Jingu AI session."
Write-Host "Chat window: type task requests, decisions, corrections, or /exit."
Write-Host "Monitor window: prints full flow, inputs, outputs, and diagnostics."
Write-Host "Sandbox: $Sandbox"
Write-Host "Logs: $LogDir"
Write-Host "Readable pointer: $ReadablePointer"
Write-Host "Method: $Method"
