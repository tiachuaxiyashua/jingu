param(
    [string] $Sandbox,
    [string] $LogDir,
    [string] $Config,
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"

function ConvertTo-SingleQuotedLiteral {
    param([string] $Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not $Sandbox) {
    $Sandbox = Join-Path $env:TEMP ("jingu-ai-sandbox-" + [guid]::NewGuid().ToString("N"))
}
if (-not $LogDir) {
    $LogDir = Join-Path $RepoRoot "local-ai-logs"
}

$RepoLiteral = ConvertTo-SingleQuotedLiteral $RepoRoot
$SandboxLiteral = ConvertTo-SingleQuotedLiteral $Sandbox
$LogDirLiteral = ConvertTo-SingleQuotedLiteral $LogDir

$ConfigArgs = ""
if ($Config) {
    $ConfigLiteral = ConvertTo-SingleQuotedLiteral $Config
    $ConfigArgs = " --config $ConfigLiteral"
}

$MonitorCommand = "& { Set-Location -LiteralPath $RepoLiteral; python -m jingu.cli ai monitor --sandbox $SandboxLiteral --log-dir $LogDirLiteral --wait-seconds 3600 }"
$ChatCommand = "& { Set-Location -LiteralPath $RepoLiteral; python -m jingu.cli ai chat --sandbox $SandboxLiteral --log-dir $LogDirLiteral$ConfigArgs }"

if ($DryRun) {
    Write-Host "Monitor command: $MonitorCommand"
    Write-Host "Chat command: $ChatCommand"
    Write-Host "Sandbox: $Sandbox"
    Write-Host "Logs: $LogDir"
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
