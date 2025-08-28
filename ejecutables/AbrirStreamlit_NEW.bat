@echo off
setlocal

REM === Configuración ===
set "ENV_NAME=compara_prg"
set "PROY=E:\Aplicaciones\Nuevo_PRG\Compara_PRG"
set "REQS=%PROY%\requirements.txt"
set "APP=%PROY%\src\compara_prg\viz\streamlit_app_consulta_Api"

REM === Verificar si existe el ambiente conda ===
set "ENV_FOUND="
for /f "tokens=* delims=" %%A in ('
  conda env list ^| findstr /i /c:" %ENV_NAME% " /c:"\%ENV_NAME%" /c:"/%ENV_NAME%" /c:"%ENV_NAME% "
') do set "ENV_FOUND=1"

if not defined ENV_FOUND (
  echo [INFO] No existe el ambiente "%ENV_NAME%". Creando con Python 3.11...
  conda create -y -n %ENV_NAME% python=3.11 || (echo [ERROR] No se pudo crear el ambiente. & pause & exit /b 1)
)

REM === Activar ambiente ===
call conda activate %ENV_NAME% || (echo [ERROR] No se pudo activar el ambiente. & pause & exit /b 1)

REM === Ir a la raíz del proyecto ===
cd /d "%PROY%"

REM === Verificar/instalar dependencias declaradas ===
if exist "%REQS%" (
  echo [INFO] Verificando dependencias desde "%REQS%"...
  REM 👇 Silencia stdout, muestra solo errores
  python -m pip install -r "%REQS%" -q >nul 2>&1 || (echo [ERROR] Fallo instalando dependencias. & pause & exit /b 1)
) else (
  echo [WARN] No existe requirements.txt en "%REQS%". Saltando instalación.
)


REM === Clave: layout src/ para que Python encuentre el paquete ===
set "PYTHONPATH=%PROY%\src;%PYTHONPATH%"

REM === Ejecutar Streamlit ===
python -m streamlit run "%APP%"

pause
endlocal
