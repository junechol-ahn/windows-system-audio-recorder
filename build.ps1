$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = "C:\Users\junec\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$ffmpegPath = Join-Path $projectRoot "vendor\ffmpeg\ffmpeg.exe"
$distPath = Join-Path $projectRoot "dist"
$buildPath = Join-Path $projectRoot "build"
$specPath = Join-Path $projectRoot "build\system_audio_recorder.spec"
$appPath = Join-Path $projectRoot "app.py"

if (-not (Test-Path $pythonExe)) {
    throw "번들 Python을 찾지 못했습니다: $pythonExe"
}

if (-not (Test-Path $ffmpegPath)) {
    throw "ffmpeg.exe가 없습니다. vendor\ffmpeg\ffmpeg.exe 경로에 파일을 추가해 주세요."
}

if (-not (Test-Path $appPath)) {
    throw "app.py를 찾지 못했습니다: $appPath"
}

New-Item -ItemType Directory -Force -Path $buildPath | Out-Null

$specContent = @"
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs

hiddenimports = []
binaries = collect_dynamic_libs('soundcard')
binaries += [(r'$ffmpegPath', '.')]

a = Analysis(
    [r'$appPath'],
    pathex=[r'$projectRoot'],
    binaries=binaries,
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SystemAudioRecorder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
"@

Set-Content -Path $specPath -Value $specContent -Encoding UTF8

& $pythonExe -m PyInstaller --noconfirm --clean --distpath $distPath --workpath $buildPath $specPath
