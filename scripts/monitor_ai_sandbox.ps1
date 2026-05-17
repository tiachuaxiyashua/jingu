param(
    [string] $Sandbox,
    [string] $LogDir,
    [double] $WaitSeconds = 30
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$ArgsList = @("-m", "jingu.cli", "ai", "monitor", "--wait-seconds", "$WaitSeconds")
if ($Sandbox) {
    $ArgsList += @("--sandbox", $Sandbox)
}
if ($LogDir) {
    $ArgsList += @("--log-dir", $LogDir)
}

python @ArgsList
