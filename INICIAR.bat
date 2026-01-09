@echo off
chcp 65001 > nul
title Sistema de Deteccion de Fraude
color 0B

echo.
echo  ==============================================================
echo       SISTEMA DE DETECCION DE FRAUDE - MERCADO PAGO STYLE
echo  ==============================================================
echo.

:: Verificar si existe venv
if exist "venv" goto LIMPIAR

:INSTALAR
echo  [!] Entorno virtual no encontrado.
echo  [+] Creando entorno virtual...
python -m venv venv
echo  [+] Instalando dependencias...
call venv\Scripts\activate.bat
pip install fastapi uvicorn[standard] pydantic jinja2 python-multipart pandas numpy scikit-learn --quiet
echo  [OK] Instalacion completada.
echo.

:LIMPIAR
:: Limpiar cache de Python para asegurar que tome los cambios
echo  [+] Limpiando cache...
if exist "api\__pycache__" rd /s /q "api\__pycache__"
if exist "api\routes\__pycache__" rd /s /q "api\routes\__pycache__"
if exist "api\models\__pycache__" rd /s /q "api\models\__pycache__"
if exist "pipeline\__pycache__" rd /s /q "pipeline\__pycache__"
echo  [OK] Cache limpiado.
echo.

:INICIAR
echo  [+] Iniciando servidor...
echo.
echo  ---------------------------------------------------------------
echo   ACCESOS:
echo   Dashboard:  http://localhost:8000
echo   API Docs:   http://localhost:8000/docs
echo  ---------------------------------------------------------------
echo.
echo  Cierra esta ventana para detener el servidor.
echo.

:: Matar cualquier proceso en el puerto 8000 (por si quedo algo colgado)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

:: Esperar un segundo
timeout /t 1 /nobreak >nul

:: Abrir navegador con parametro para evitar cache
start "" "http://localhost:8000?nocache=%random%"

:: Iniciar servidor
venv\Scripts\python.exe -m uvicorn api.main:app --port 8000 --host 127.0.0.1

pause
