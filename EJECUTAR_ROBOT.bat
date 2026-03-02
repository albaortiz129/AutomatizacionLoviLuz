@echo off
title ROBOT SINCRONIZADOR
color 0b

:: 1. Intentamos cerrar solo procesos de Chromium de Playwright (menos agresivo)
taskkill /f /im chrome.exe /t >nul 2>&1
taskkill /f /im chromium.exe /t >nul 2>&1

:: 2. Nos movemos a la carpeta del script
cd /d "C:\Users\PC\Documents\GitHub\AutomatizacionLoviLuz"

:: 3. Verificamos el entorno virtual
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encuentra el entorno virtual .venv
    echo Por favor, ejecuta: python -m venv .venv
    pause
    exit
)

set "PYTHON=.venv\Scripts\python.exe"

echo ==========================================
echo    INICIANDO SINCRONIZACION...
echo ==========================================
echo.

:: 4. Ejecutamos el script
"%PYTHON%" sincronizador.py

:: 5. Si el script falla, el error se queda en pantalla antes de cerrar
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] El robot se ha detenido por un fallo critico.
)

echo.
echo ==========================================
echo    PROCESO FINALIZADO
echo ==========================================
pause