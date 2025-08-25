@echo off
set ENV_NAME=compara_prg
set REQ_FILE=requirements.txt

REM Comprobar si existe el entorno
conda env list | findstr /i "%ENV_NAME%" >nul
if errorlevel 1 (
    echo [INFO] Creando entorno %ENV_NAME%...
    conda create -y -n %ENV_NAME% python=3.10
    conda activate %ENV_NAME%
    pip install -r "%REQ_FILE%"
) else (
    echo [INFO] Activando entorno existente %ENV_NAME%...
    conda activate %ENV_NAME%
)

REM Ir a carpeta del proyecto
cd /d "E:\Aplicaciones\Nuevo_PRG\Compara_PRG\Querys"

REM Ejecutar Streamlit
python -m streamlit run "streamlit_app.py"

pause



