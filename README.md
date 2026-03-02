# AutomatizacionLoviLuz

Robot de sincronización entre WolfCRM e Ignis usando Playwright (Python).

## Cómo arrancar (Windows)

1) Primera vez (dependencias):
   - Ejecuta `INSTALADOR_INICIAL.bat`

2) Credenciales:
   - Copia `.env.example` a `.env` (si no existe) y revisa/define:
     - `WOLF_USER`, `WOLF_PASS`
     - `IGNIS_USER`, `IGNIS_PASS`

3) Ejecutar:
   - Doble click a `EJECUTAR_ROBOT.bat`
   - O en PowerShell:
     - `.\.venv\Scripts\python.exe .\sincronizador.py`

## Notas

- La sesión persistente de Playwright se guarda en `SesionIgnis\`.
- Los logs se guardan en `LOGS\` (por día).
