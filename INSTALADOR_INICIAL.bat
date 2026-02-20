@echo off
title Instalador de Dependencias - Sincronizador
echo ==========================================
echo   INSTALANDO LIBRERIAS PARA EL ROBOT
echo ==========================================
echo.

:: 1. Verificamos si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no se agrego al PATH.
    echo Por favor, instala Python antes de continuar.
    pause
    exit
)

:: 2. Instalamos las dependencias necesarias
echo [1/3] Instalando Playwright y Dotenv...
pip install playwright python-dotenv

:: 3. Instalamos el navegador Chromium de Playwright
echo [2/3] Descargando navegador interno (Chromium)...
playwright install chromium

echo.
echo [3/3] ¡TODO LISTO!
echo Ya puedes cerrar esta ventana y usar el ejecutor diario.
echo ==========================================
pause