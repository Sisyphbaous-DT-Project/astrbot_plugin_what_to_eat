param(
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$metadataPath = Join-Path $repoRoot "metadata.yaml"

if (-not (Test-Path $metadataPath)) {
    throw "metadata.yaml not found at $metadataPath"
}

$metadataContent = Get-Content $metadataPath -Raw
$nameMatch = [regex]::Match($metadataContent, '(?m)^name:\s*(.+?)\s*$')
$versionMatch = [regex]::Match($metadataContent, '(?m)^version:\s*(.+?)\s*$')

if (-not $nameMatch.Success -or -not $versionMatch.Success) {
    throw "Failed to read name/version from metadata.yaml"
}

$pluginName = $nameMatch.Groups[1].Value.Trim()
$version = $versionMatch.Groups[1].Value.Trim()
$artifactName = "$pluginName-$version.zip"
$outputRoot = Join-Path $repoRoot $OutputDir
$stagingRoot = Join-Path $outputRoot $pluginName
$artifactPath = Join-Path $outputRoot $artifactName

if (Test-Path $stagingRoot) {
    Remove-Item $stagingRoot -Recurse -Force
}

if (Test-Path $artifactPath) {
    Remove-Item $artifactPath -Force
}

New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null

$includeFiles = @(
    "__init__.py",
    "_conf_schema.json",
    "food_data.py",
    "image_manager.py",
    "LICENSE",
    "logo.png",
    "main.py",
    "metadata.yaml",
    "README.md",
    "rate_limiter.py",
    "responder.py"
)

foreach ($relativePath in $includeFiles) {
    $sourcePath = Join-Path $repoRoot $relativePath
    if (-not (Test-Path $sourcePath)) {
        throw "Release file missing: $relativePath"
    }

    $targetPath = Join-Path $stagingRoot $relativePath
    $targetDir = Split-Path -Parent $targetPath
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
    Copy-Item $sourcePath $targetPath -Force
}

Compress-Archive -Path (Join-Path $stagingRoot '*') -DestinationPath $artifactPath -CompressionLevel Optimal

Write-Output "Created $artifactPath"
