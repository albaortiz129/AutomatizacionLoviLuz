#!/usr/bin/env python3
"""
Prueba directa de extracción de texto y PDF
Sin necesidad de servidor FastAPI
"""
import json
from cerebro import analizar_consulta_loviluz

print("=" * 80)
print("🧪 PRUEBA DIRECTA DE EXTRACCIÓN")
print("=" * 80)

# TEST 1: Texto simple
print("\n1️⃣ TEST TEXTO SIMPLE")
print("-" * 80)

mensaje = """
Hola, soy Juan Carlos López Martínez con DNI 45678901C.
Quiero cambiar de compañía de luz.
Mi CUPS es ES1234567890123456789012.
Vivo en Calle Mayor 42, 2ºA, Madrid 28001.
Compañía actual: Iberdrola
Tarifa: 2.0TD
"""

print(f"📝 Analizando: {mensaje.strip()[:100]}...")
resultado = analizar_consulta_loviluz(mensaje)
datos = json.loads(resultado)

print("\n✅ DATOS EXTRAÍDOS:")
for clave, valor in datos.items():
    if valor != "PENDIENTE":
        print(f"  ✔️  {clave}: {valor}")
    else:
        print(f"  ⚠️  {clave}: {valor}")

# TEST 2: Verificar campos clave
print("\n\n2️⃣ VALIDACIÓN DE CAMPOS CRÍTICOS")
print("-" * 80)

campos_criticos = {
    "Customer__NAME": "Nombre del cliente",
    "EnergyContract__FIRMANTE_DNI": "DNI firmante",
    "EnergyContract__NAME": "CUPS",
    "EnergyContract__CUPS_ADDRESS": "Dirección",
    "EnergyContract__CUPS_POSTAL_CODE": "Código postal",
    "EnergyContract__COMERCIALIZADORA": "Compañía actual",
    "EnergyContract__SUMINISTRO": "Tipo suministro",
}

print(f"{'Campo':<40} {'Valor Extraído':<40}")
print("-" * 80)
for campo, desc in campos_criticos.items():
    valor = datos.get(campo, "PENDIENTE")
    estado = "✅" if valor != "PENDIENTE" else "⚠️"
    print(f"{estado} {desc:<38} {str(valor)[:35]}")

print("\n" + "=" * 80)
print("✅ PRUEBA COMPLETADA")
print("=" * 80)
