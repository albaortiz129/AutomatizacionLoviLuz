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
if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creando entorno virtual local (.venv)...
    python -m venv .venv
)

set "VPY=.venv\Scripts\python.exe"
set "VPW=.venv\Scripts\playwright.exe"

echo [2/4] Actualizando pip...
"%VPY%" -m pip install --upgrade pip

echo [3/4] Instalando Playwright y Dotenv...
"%VPY%" -m pip install playwright python-dotenv

:: 3. Instalamos el navegador Chromium de Playwright
echo [4/4] Descargando navegador interno (Chromium)...
"%VPW%" install chromium

echo.
echo [OK] TODO LISTO!
echo Ya puedes cerrar esta ventana y usar el ejecutor diario.
echo ==========================================
pause
