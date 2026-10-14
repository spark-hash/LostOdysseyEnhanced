@echo off
setlocal
call "%~dp0vs-buildtools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
set "PATH=%~dp0vs-buildtools\VC\Tools\Llvm\x64\bin;%~dp0vs-buildtools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%~dp0vs-buildtools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cd /d "%~dp0..\upstream"
cmake --build out\build\windows-clang --target LoFramePlanTest LoFramePacerTest --parallel 4
if errorlevel 1 exit /b 1
out\build\windows-clang\LostOdysseyRecomp\LoFramePlanTest.exe
if errorlevel 1 exit /b 1
out\build\windows-clang\LostOdysseyRecomp\LoFramePacerTest.exe
exit /b %errorlevel%
