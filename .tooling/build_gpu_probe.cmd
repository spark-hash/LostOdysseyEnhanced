@echo off
setlocal
call "%~dp0vs-buildtools\VC\Auxiliary\Build\vcvars64.bat" > nul
cd /d "%~dp0.."
cl /nologo /std:c++20 /EHsc /MT /O2 /W3 /I.tooling\streamline\include /I.tooling\nvidia-dlss\include /Iupstream\thirdparty\plume\contrib\Vulkan-Headers\include /Iupstream\tools\XenonRecomp\thirdparty\tomlplusplus\vendor enhancements\gpu_capabilities.cpp /Fo:downloads\gpu_capabilities.obj /Fe:downloads\GpuCapabilities.exe /link .tooling\nvidia-dlss\lib\Windows_x86_64\x64\nvsdk_ngx_s.lib d3d12.lib dxgi.lib wintrust.lib crypt32.lib advapi32.lib user32.lib shell32.lib ole32.lib
exit /b %errorlevel%
