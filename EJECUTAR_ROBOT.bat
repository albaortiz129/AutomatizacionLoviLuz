@echo off
title Robot Sincronizador Wolf-Ignis
echo ==========================================
echo   INICIANDO SINCRONIZACION DE CONTRATOS
echo ==========================================
echo.

:: Cambia a la carpeta donde esta este archivo .bat
cd /d "C:\xampp\htdocs\GitHub\AutomatizacionLoviLuz"

:: Ejecuta el script de Python (Asegurate que tu archivo se llama sincronizar.py)
python sincronizador.py

echo.
echo ==========================================
echo   PROCESO FINALIZADO
echo ==========================================
echo.
pause