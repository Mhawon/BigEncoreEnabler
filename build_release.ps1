param(
    [string]$SdkArchivePath
)

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$distDir = Join-Path $repoRoot 'dist'
$archiveDir = Join-Path $distDir 'archives'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$bundlePath = Join-Path $archiveDir "BigEncoreEnabler-Full-Bundle-$stamp.zip"
$latestBundlePath = Join-Path $distDir 'BigEncoreEnabler-Full-Bundle.zip'
$sdkUrl = 'https://github.com/bl-sdk/oak2-mod-manager/releases/download/v0.3/oak2-sdk.zip'
$expectedSdkSha256 = '602675446ABED184169FA158BE3C8BC81777A71203581E4A248ECA8A3D00B5C7'

if (Test-Path -LiteralPath $bundlePath) {
    throw "Bundle already exists: $bundlePath. Move it aside before rebuilding."
}

New-Item -ItemType Directory -Path $distDir -Force | Out-Null
New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) "BigEncoreEnabler-$([guid]::NewGuid().ToString('N'))"
$tempPrefix = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
$resolvedTemp = [IO.Path]::GetFullPath($tempRoot)
if (-not $resolvedTemp.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use a temporary path outside the temp directory: $resolvedTemp"
}

$sdkArchive = Join-Path $tempRoot 'oak2-sdk.zip'
$stageDir = Join-Path $tempRoot 'bundle-root'

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    if ($SdkArchivePath) {
        if (-not (Test-Path -LiteralPath $SdkArchivePath -PathType Leaf)) {
            throw "SDK archive not found: $SdkArchivePath"
        }
        Copy-Item -LiteralPath $SdkArchivePath -Destination $sdkArchive
    }
    else {
        Invoke-WebRequest -Uri $sdkUrl -OutFile $sdkArchive
    }

    $actualSdkSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sdkArchive).Hash
    if ($actualSdkSha256 -ne $expectedSdkSha256) {
        throw "Official SDK hash mismatch. Expected $expectedSdkSha256; got $actualSdkSha256"
    }

    Expand-Archive -LiteralPath $sdkArchive -DestinationPath $stageDir

    $modDir = Join-Path $stageDir 'sdk_mods\BigEncoreEnabler'
    New-Item -ItemType Directory -Path $modDir -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot '__init__.py') -Destination (Join-Path $modDir '__init__.py')
    Copy-Item -LiteralPath (Join-Path $repoRoot 'umg_notification.py') -Destination (Join-Path $modDir 'umg_notification.py')
    Copy-Item -LiteralPath (Join-Path $repoRoot 'README.md') -Destination (Join-Path $modDir 'README.md')
    $iconPath = Join-Path $repoRoot 'bencore_icon.png'
    if (-not (Test-Path -LiteralPath $iconPath -PathType Leaf)) {
        throw "Icon asset not found: $iconPath"
    }
    Copy-Item -LiteralPath $iconPath -Destination (Join-Path $modDir 'bencore_icon.png')
    Copy-Item -LiteralPath (Join-Path $repoRoot 'README.md') -Destination (Join-Path $stageDir 'README-BigEncoreEnabler.txt')
    Copy-Item -LiteralPath (Join-Path $repoRoot 'THIRD-PARTY-NOTICES.md') -Destination (Join-Path $stageDir 'THIRD-PARTY-NOTICES.txt')

    Compress-Archive -Path (Join-Path $stageDir '*') -DestinationPath $bundlePath -CompressionLevel Optimal

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $bundle = [System.IO.Compression.ZipFile]::OpenRead($bundlePath)
    try {
        $entryNames = @($bundle.Entries | ForEach-Object { $_.FullName.Replace('\', '/') })
        $requiredEntries = @(
            'OakGame/Binaries/Win64/dsound.dll',
            'OakGame/Binaries/Win64/Plugins/pyunrealsdk.dll',
            'sdk_mods/__main__.py',
            'sdk_mods/mods_base.sdkmod',
            'sdk_mods/BigEncoreEnabler/__init__.py',
            'sdk_mods/BigEncoreEnabler/umg_notification.py',
            'sdk_mods/BigEncoreEnabler/bencore_icon.png',
            'README-BigEncoreEnabler.txt',
            'THIRD-PARTY-NOTICES.txt'
        )
        foreach ($entryName in $requiredEntries) {
            if ($entryNames -notcontains $entryName) {
                throw "Bundle validation failed; missing $entryName"
            }
        }
    }
    finally {
        $bundle.Dispose()
    }

    Copy-Item -LiteralPath $bundlePath -Destination $latestBundlePath -Force
    Write-Output "Built timestamped full SDK + mod bundle: $bundlePath"
    Write-Output "Updated latest full bundle: $latestBundlePath"
}
finally {
    if (Test-Path -LiteralPath $resolvedTemp) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}
