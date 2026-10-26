# Build Team Code Link.exe from this folder.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3 -m pip install pyinstaller
py -3 -m PyInstaller --noconfirm --clean TeamCodeLink.spec
Write-Host "Built dist\Team Code Link.exe"
