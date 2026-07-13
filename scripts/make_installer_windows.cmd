@echo off
rem Copyright (c) 2026 The Sequence Group.
rem SPDX-License-Identifier: Apache-2.0
rem
rem Build the Sequence RV Windows installer (SequenceRV-<version>-Setup.exe).
rem
rem   scripts\make_installer_windows.cmd [stage_dir]
rem
rem stage_dir defaults to _external\OpenRV\_build\stage\app and must be a
rem built + bundled distribution (scripts/build_openrv.sh, make packages,
rem scripts/bundle_release.sh). Requires Inno Setup 6 on this machine:
rem https://jrsoftware.org/isinfo.php
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "STAGE=%~1"
if "%STAGE%"=="" set "STAGE=%ROOT%\_external\OpenRV\_build\stage\app"
if not exist "%STAGE%\" (
    echo error: stage directory not found: %STAGE% 1>&2
    echo        build and bundle first - see docs\building-openrv.md 1>&2
    exit /b 1
)
if not exist "%STAGE%\bin\seqrv.cmd" (
    echo error: %STAGE% is not bundled ^(bin\seqrv.cmd missing^) 1>&2
    echo        run: bash scripts/bundle_release.sh 1>&2
    exit /b 1
)

set /p VERSION=<"%ROOT%\VERSION"

set "ISCC="
where iscc.exe >nul 2>nul && set "ISCC=iscc.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo error: Inno Setup 6 ^(ISCC.exe^) not found - install from https://jrsoftware.org/isinfo.php 1>&2
    exit /b 1
)

if not exist "%ROOT%\dist" mkdir "%ROOT%\dist"

"%ISCC%" /DStageDir="%STAGE%" /DRepoRoot="%ROOT%" /DAppVersion=%VERSION% ^
    /O"%ROOT%\dist" "%ROOT%\installers\windows\sequence-rv.iss"
if errorlevel 1 exit /b 1

echo.
echo Installer written to %ROOT%\dist\SequenceRV-%VERSION%-Setup.exe
endlocal
