$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$AppName = "Tidal Playlist Creator"
$IconPath = "resources/icons/app.ico"

if (-not $IsWindows) {
    throw "This build script must run on Windows."
}

$Arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", $AppName,
    "--collect-all", "tidalapi"
)

if (Test-Path $IconPath) {
    $Arguments += @("--icon", $IconPath)
}

$Arguments += "main.py"

& $PythonBin @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$Executable = Join-Path "dist" "$AppName.exe"
if (-not (Test-Path $Executable -PathType Leaf)) {
    throw "Expected executable was not generated: $Executable"
}

Write-Host "Built: $Executable"
