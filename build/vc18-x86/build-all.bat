@echo off
setlocal enabledelayedexpansion
if "%VS180COMNTOOLS%" == "" (
for /f "usebackq tokens=1* delims=: " %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest `) do (
  if /i "%%i"=="productPath" (
        set VS180COMNTOOLS=%%j
)
)
)
setx VS180COMNTOOLS "!VS180COMNTOOLS!"
if "%VS180COMNTOOLS%" == "" (
  msg "%username%" "Visual Studio 18 not detected"
  exit 1
)
if not exist x265.sln (
  call make-solutions.bat
)
if exist x265.sln (
  call "%VS180COMNTOOLS%\..\..\tools\VsDevCmd.bat"
  MSBuild /property:Configuration="Release" x265.sln
  MSBuild /property:Configuration="Debug" x265.sln
  MSBuild /property:Configuration="RelWithDebInfo" x265.sln
)
