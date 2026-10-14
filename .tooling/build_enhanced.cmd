@echo off
setlocal
set "LO_VCVARS64=%~dp0vs-buildtools\VC\Auxiliary\Build\vcvars64.bat"
set "LLVM_ROOT=%~dp0vs-buildtools\VC\Tools\Llvm\x64"
if not defined LO_PYTHON set "LO_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PATH=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd;%PATH%"
cd /d "%~dp0..\upstream"
if not exist ..\downloads mkdir ..\downloads
if "%1"=="resume" goto runtime
call tools\build_tools.bat > ..\downloads\build-tools.log 2>&1
if errorlevel 1 exit /b 1
if not exist LostOdysseyRecompLib\ppc mkdir LostOdysseyRecompLib\ppc
out\build\tools\XenonRecomp\XenonRecomp\XenonRecomp.exe LostOdysseyRecompLib\config\LostOdysseyRecomp.toml tools\XenonRecomp\XenonUtils\ppc_context.h > ..\downloads\ppc-generation.log 2>&1
if errorlevel 1 exit /b 1
"%LO_PYTHON%" -u tools\ppc_codegen.py barriers >> ..\downloads\ppc-generation.log 2>&1
if errorlevel 1 exit /b 1
out\build\tools\xexdump.exe LostOdysseyRecompLib\private\disc1\default.xex LostOdysseyRecompLib\private\image_disc1.bin >> ..\downloads\ppc-generation.log 2>&1
if errorlevel 1 exit /b 1
:runtime
call tools\setup_windows.bat
if errorlevel 1 exit /b 1
cmake --preset windows-clang -DCMAKE_NINJA_CMCLDEPS_RC=OFF -DPython3_EXECUTABLE="%LO_PYTHON%" -DLO_BUILD_TOOLS=OFF -DLO_ENABLE_DLSS=ON -DLO_REQUIRE_DLSS=ON -DLO_DLSS_SDK_ROOT="%~dp0nvidia-dlss" -DLO_ENABLE_STREAMLINE_FG=ON -DLO_ENABLE_D3D12_DLSS_FG=ON -DLO_STREAMLINE_SDK_ROOT="%~dp0streamline" -DFETCHCONTENT_SOURCE_DIR_LO_FFMPEG="%~dp0ffmpeg" > ..\downloads\configure-runtime.log 2>&1
if errorlevel 1 exit /b 1
cmake --build out\build\windows-clang --target LostOdysseyRecomp --parallel 8 > ..\downloads\build-runtime.log 2>&1
exit /b %errorlevel%
