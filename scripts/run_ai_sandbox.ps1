param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $Message,

    [string] $Sandbox,
    [string] $LogDir,
    [string] $Config
)

$ErrorActionPreference = "Stop"

$ArgsList = @("-m", "jingu.cli", "ai", "run", "--message", $Message)
if ($Sandbox) {
    $ArgsList += @("--sandbox", $Sandbox)
}
if ($LogDir) {
    $ArgsList += @("--log-dir", $LogDir)
}
if ($Config) {
    $ArgsList += @("--config", $Config)
}

python @ArgsList
