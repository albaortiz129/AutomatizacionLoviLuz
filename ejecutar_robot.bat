@echo off
title Ejecutando Robot de Sincronizacion Wolf-Ignis
:: Cambia la siguiente linea por la carpeta donde esta tu script
cd /d "C:\xampp\htdocs\GitHub\AutomatizacionLoviLuz"

echo.
echo  ======================================================
echo     INICIANDO ROBOT DE ACTUALIZACION DE CONTRATOS
echo  ======================================================
echo.

:: Ejecuta el script de Python
python sincronizar_contratos.py

echo.
echo  ======================================================
echo     PROCESO FINALIZADO. Pulsa una tecla para salir.
echo  ======================================================
pause