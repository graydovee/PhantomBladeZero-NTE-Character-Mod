param(
  [Parameter(Mandatory=$true)][string]$Version,
  [string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path,
  [string]$OutDir = ""
)
$ErrorActionPreference = "Stop"

$moduleDir = Join-Path $Workspace "App"
if (-not (Test-Path (Join-Path $moduleDir "go.mod"))) { throw "Module path must contain go.mod: $moduleDir" }

if (-not $OutDir) { $OutDir = Join-Path $Workspace "Release" }
$mainDir = Join-Path $moduleDir "cmd\pbzmodkit"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$env:CGO_ENABLED = "0"
$env:GOOS = "windows"
$env:GOARCH = "amd64"
$env:GOPROXY = "https://goproxy.cn,direct"

$ldflags = "-H windowsgui -X pbzmodkit/internal/ui.Version=$Version"

Write-Host "=== 1. 生成资源 (.syso) ===" -ForegroundColor Cyan
Push-Location $mainDir
try {
  $winres = (Get-Command go-winres -ErrorAction SilentlyContinue).Source
  if (-not $winres) { $winres = Join-Path (& go env GOPATH) "bin\go-winres.exe" }
  & $winres simply `
    --manifest gui `
    --icon "assets\icon.ico" `
    --product-version $Version `
    --file-version $Version `
    --product-name "PBZ Mod Kit" `
    --file-description "Phantom Blade Zero Mod Manager" `
    --original-filename "PBZModKit.exe"
  if ($LASTEXITCODE -ne 0) { throw "go-winres 失败 ($LASTEXITCODE)" }
  Get-ChildItem *.syso | Select-Object Name, Length | Format-Table -AutoSize
} finally { Pop-Location }

Write-Host "=== 2. 编译 GUI + CLI ===" -ForegroundColor Cyan
Push-Location $moduleDir
try {
  foreach ($name in @("PBZModKit.exe", "PBZModKit-cli.exe")) {
    & go build -trimpath -ldflags $ldflags -o (Join-Path $OutDir $name) .\cmd\pbzmodkit
    if ($LASTEXITCODE -ne 0) { throw "go build $name 失败 ($LASTEXITCODE)" }
  }
} finally { Pop-Location }

foreach ($name in @("PBZModKit.exe", "PBZModKit-cli.exe")) {
  $exe = Join-Path $OutDir $name
  if (-not (Test-Path $exe)) { throw "没有生成 $name" }
  $fi = Get-Item $exe
  Write-Host ("产物: {0}  {1:N2} MB" -f $fi.FullName, ($fi.Length / 1MB)) -ForegroundColor Green
}
