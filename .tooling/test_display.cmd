@echo off
setlocal
call "%~dp0vs-buildtools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
"%~dp0vs-buildtools\VC\Tools\Llvm\x64\bin\clang-cl.exe" /std:c++20 /EHsc /I"%~dp0..\upstream\LostOdysseyRecomp" "%~dp0check_display.cpp" /Fe:"%~dp0check_display.exe" /Fo:"%~dp0check_display.obj"
if errorlevel 1 exit /b 1
"%~dp0check_display.exe"
exit /b %errorlevel%
