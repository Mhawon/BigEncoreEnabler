$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$distDir = Join-Path $repoRoot 'dist'
$archiveDir = Join-Path $distDir 'archives'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$bundlePath = Join-Path $archiveDir "BigEncoreEnabler-Plugin-$stamp.zip"
$latestBundlePath = Join-Path $distDir 'BigEncoreEnabler-Plugin.zip'
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) "BigEncoreEnabler-plugin-$([guid]::NewGuid().ToString('N'))"

if (Test-Path -LiteralPath $bundlePath) {
    throw "Bundle already exists: $bundlePath. Move it aside before rebuilding."
}

try {
    $modDir = Join-Path $tempRoot 'sdk_mods\BigEncoreEnabler'
    New-Item -ItemType Directory -Path $modDir -Force | Out-Null
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

    foreach ($file in @('__init__.py', 'umg_notification.py', 'README.md')) {
        Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination (Join-Path $modDir $file)
    }

    $iconPath = Join-Path $repoRoot 'bencore_icon.png'
    if (-not (Test-Path -LiteralPath $iconPath -PathType Leaf)) {
        throw "Icon asset not found: $iconPath"
    }
    Copy-Item -LiteralPath $iconPath -Destination (Join-Path $modDir 'bencore_icon.png')

    Compress-Archive -Path (Join-Path $tempRoot 'sdk_mods') -DestinationPath $bundlePath -CompressionLevel Optimal
    Copy-Item -LiteralPath $bundlePath -Destination $latestBundlePath -Force
    Write-Output "Built timestamped standalone plugin archive: $bundlePath"
    Write-Output "Updated latest standalone plugin archive: $latestBundlePath"
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
