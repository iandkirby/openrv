@echo off
rem Copyright (c) 2026 The Sequence Group.
rem SPDX-License-Identifier: Apache-2.0
rem
rem seqrvio — The Sequence Group launcher for rvio on Windows.
rem
rem   seqrvio [--show SHOW] [--rvio path\to\rvio.exe] [rvio args...]
rem
rem Mirrors bin/seqrvio: exports the studio environment (including per-show
rem OCIO) and runs the real rvio.exe, so batch renders match review color.
setlocal

set "SELF=%~dp0"
if not defined SEQ_KIT_ROOT (
    if exist "%SELF%..\sequence\" (
        for %%I in ("%SELF%..\sequence") do set "SEQ_KIT_ROOT=%%~fI"
    ) else (
        for %%I in ("%SELF%..") do set "SEQ_KIT_ROOT=%%~fI"
    )
)

set "RVIO_BIN=%SEQ_RVIO_BIN%"
set "PASS="

:parse
if "%~1"=="" goto resolve_ocio
if /i "%~1"=="--show" ( set "SEQ_SHOW=%~2" & shift & shift & goto parse )
if /i "%~1"=="--rvio" ( set "RVIO_BIN=%~2" & shift & shift & goto parse )
set PASS=%PASS% "%~1"
shift
goto parse

:resolve_ocio
if defined OCIO goto find_rvio
if not defined SEQ_SHOW goto find_rvio
set "SEQ_RULES=%SEQ_OCIO_RULES%"
if not defined SEQ_RULES set "SEQ_RULES=%SEQ_KIT_ROOT%\configs\ocio_rules.json"
if not exist "%SEQ_RULES%" goto find_rvio
if not exist "%SEQ_KIT_ROOT%\scripts\resolve_ocio.py" goto find_rvio
where python >nul 2>nul
if errorlevel 1 goto find_rvio
for /f "usebackq delims=" %%O in (`python "%SEQ_KIT_ROOT%\scripts\resolve_ocio.py" "%SEQ_RULES%" "%SEQ_SHOW%"`) do set "OCIO=%%O"
if defined OCIO echo seqrvio: OCIO=%OCIO% 1>&2

:find_rvio
if defined RVIO_BIN goto run
if exist "%SELF%rvio.exe" ( set "RVIO_BIN=%SELF%rvio.exe" & goto run )
set "RVIO_BIN=rvio"

:run
"%RVIO_BIN%" %PASS%
endlocal
