param(
    [string] $Sandbox,
    [string] $LogDir,
    [double] $WaitSeconds = 30
)

$ErrorActionPreference = "Stop"

$ArgsList = @("-m", "jingu.cli", "ai", "monitor", "--wait-seconds", "$WaitSeconds")
if ($Sandbox) {
    $ArgsList += @("--sandbox", $Sandbox)
}
if ($LogDir) {
    $ArgsList += @("--log-dir", $LogDir)
}

python @ArgsList
