@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
if errorlevel 1 exit /b %errorlevel%
if not exist "%~dp0bin" mkdir "%~dp0bin"
cl /nologo /EHsc /std:c++17 /MD /O2 /DFBXSDK_SHARED ^
  /I"D:\UE\UE_5.8\Engine\Source\ThirdParty\FBX\2020.2\include" ^
  "%~dp0fbx_motion_normalizer.cpp" ^
  /Fe:"%~dp0bin\fbx_motion_normalizer.exe" ^
  /link /LIBPATH:"D:\UE\UE_5.8\Engine\Source\ThirdParty\FBX\2020.2\lib\vs2017\x64\release" libfbxsdk.lib
exit /b %errorlevel%
