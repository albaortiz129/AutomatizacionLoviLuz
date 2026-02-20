@echo off
title ROBOT SINCRONIZADOR
color 0b

:: 1. Cerramos procesos que puedan bloquear la carpeta de sesion
taskkill /f /im chrome.exe /t >nul 2>&1

:: 2. Nos movemos a la carpeta del script
cd /d "C:\xampp\htdocs\GitHub\AutomatizacionLoviLuz"

echo ==========================================
echo    INICIANDO SINCRONIZACION...
echo ==========================================
echo.

:: 3. Ejecutamos el script
python sincronizador.py

echo.
echo ==========================================
echo    PROCESO FINALIZADO
echo ==========================================
pause   