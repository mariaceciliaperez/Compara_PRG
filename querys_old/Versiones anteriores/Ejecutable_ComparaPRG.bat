@echo off
setlocal EnableExtensions

REM Ir a la carpeta del proyecto (donde está este .bat)
pushd "%~dp0"

REM Entrar a la subcarpeta Querys (como haces en PS)
cd /d "%~dp0Querys"

REM Detectar instalación base de conda (sin rutas fijas)
for /f "delims=" %%i in ('conda info --base') do set "CONDA_BASE=%%i"

echo [INFO] Python base: %CONDA_BASE%\python.exe
"%CONDA_BASE%\python.exe" -c "import sys,streamlit; print('python:',sys.executable); print('streamlit:',streamlit.__version__)"

echo [INFO] Lanzando Streamlit...
"%CONDA_BASE%\python.exe" -m streamlit run "streamlit_app.py"

popd
pause
endlocal
