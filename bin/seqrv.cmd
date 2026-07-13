@echo off
rem Copyright (c) 2026 The Sequence Group.
rem SPDX-License-Identifier: Apache-2.0
rem
rem seqrv — The Sequence Group launcher for (Open)RV on Windows.
rem
rem   seqrv [--show SHOW] [--dailies manifest.json] [--rv path\to\rv.exe] [rv args...]
rem
rem Mirrors bin/seqrv: exports the studio environment (SEQ_SHOW,
rem SEQ_DAILIES_MANIFEST, SEQ_KIT_ROOT, OCIO) and runs the real rv.exe.
rem For arguments needing complex quoting, prefer bin/seqrv under MSYS2/Git Bash.
setlocal

set "SELF=%~dp0"
if not defined SEQ_KIT_ROOT (
    if exist "%SELF%..\sequence\" (
        for %%I in ("%SELF%..\sequence") do set "SEQ_KIT_ROOT=%%~fI"
    ) else (
        for %%I in ("%SELF%..") do set "SEQ_KIT_ROOT=%%~fI"
    )
)

set "RV_BIN=%SEQ_RV_BIN%"
set "PASS="

:parse
if "%~1"=="" goto resolve_ocio
if /i "%~1"=="--show"    ( set "SEQ_SHOW=%~2" & shift & shift & goto parse )
if /i "%~1"=="--dailies" ( set "SEQ_DAILIES_MANIFEST=%~f2" & shift & shift & goto parse )
if /i "%~1"=="--rv"      ( set "RV_BIN=%~2" & shift & shift & goto parse )
set PASS=%PASS% "%~1"
shift
goto parse

:resolve_ocio
if defined OCIO goto find_rv
if not defined SEQ_SHOW goto find_rv
set "SEQ_RULES=%SEQ_OCIO_RULES%"
if not defined SEQ_RULES set "SEQ_RULES=%SEQ_KIT_ROOT%\configs\ocio_rules.json"
if not exist "%SEQ_RULES%" goto find_rv
if not exist "%SEQ_KIT_ROOT%\scripts\resolve_ocio.py" goto find_rv
where python >nul 2>nul
if errorlevel 1 goto find_rv
for /f "usebackq delims=" %%O in (`python "%SEQ_KIT_ROOT%\scripts\resolve_ocio.py" "%SEQ_RULES%" "%SEQ_SHOW%"`) do set "OCIO=%%O"
if defined OCIO echo seqrv: OCIO=%OCIO% 1>&2

:find_rv
if defined RV_BIN goto run
if exist "%SELF%rv.exe" ( set "RV_BIN=%SELF%rv.exe" & goto run )
set "RV_BIN=rv"

:run
"%RV_BIN%" %PASS%
endlocal
