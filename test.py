import json
from cerebro import analizar_consulta_loviluz, procesar_pdf_contrato, extraer_texto_pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import tempfile
import os

print("=" * 80)
print("🧪 PRUEBAS DE EXTRACCIÓN DE DATOS - LOVILUZ")
print("=" * 80)

# ============================================================================
# TEST 1: Análisis de consulta de texto
# ============================================================================
print("\n📝 TEST 1: Análisis de consulta de texto")
print("-" * 80)

mensaje_texto = """
Hola, soy Eustaquio Habitual García, con DNI 12345678A. 
Quiero contratar un CUPS ES1234567890123456789ABC en Madrid.
Vivo en Calle Falsa 123, 3B, código postal 28010.
Quiero cambio de compañía de luz con tarifa 2.0TD desde Iberdrola.
"""

print(f"📍 Entrada: {mensaje_texto}")
resultado = analizar_consulta_loviluz(mensaje_texto)
datos = json.loads(resultado)

print("\n✅ Datos extraídos:")
for clave, valor in datos.items():
    estado = "✔️" if valor != "PENDIENTE" else "⚠️"
    print(f"  {estado} {clave}: {valor}")

# ============================================================================
# TEST 2: Crear un PDF de prueba y extraerlo
# ============================================================================
print("\n\n📄 TEST 2: Generación y lectura de PDF")
print("-" * 80)

# Crear PDF de prueba
with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
    temp_pdf = tmp.name

c = canvas.Canvas(temp_pdf, pagesize=letter)
c.setFont("Helvetica", 12)
c.drawString(50, 750, "CONTRATO DE SUMINISTRO DE ENERGÍA")
c.drawString(50, 700, "=" * 80)
c.drawString(50, 650, "DATOS DEL CLIENTE")
c.drawString(50, 620, "Nombre: Juan Fernando Martínez Ruiz")
c.drawString(50, 590, "DNI: 98765432B")
c.drawString(50, 560, "Dirección: Avenida Principal 456, Piso 2A, Barcelona")
c.drawString(50, 530, "Código Postal: 08002")
c.drawString(50, 500, "Provincia: Barcelona")
c.drawString(50, 450, "DATOS TÉCNICOS")
c.drawString(50, 420, "Punto de suministro (CUPS): ES0021567401234567890EC")
c.drawString(50, 390, "Tipo de suministro: Electricidad")
c.drawString(50, 360, "Comercializadora actual: Endesa")
c.drawString(50, 330, "Tarifa: 2.0A")
c.drawString(50, 300, "Tipo de alta: CC (Cambio Comercializadora)")
c.save()

print(f"✅ PDF creado en: {temp_pdf}")

# Extraer texto del PDF
texto_pdf = extraer_texto_pdf(temp_pdf)
print(f"\n📖 Texto extraído del PDF:\n{texto_pdf[:200]}...")

# Procesar PDF
print("\n🔍 Procesando PDF...")
resultado_pdf = procesar_pdf_contrato(temp_pdf)
datos_pdf = json.loads(resultado_pdf)

print("\n✅ Datos extraídos del PDF:")
for clave, valor in datos_pdf.items():
    estado = "✔️" if valor != "PENDIENTE" else "⚠️"
    print(f"  {estado} {clave}: {valor}")

# Limpiar
os.remove(temp_pdf)
print(f"\n🗑️ PDF de prueba eliminado")

# ============================================================================
# TEST 3: Comparación de resultados
# ============================================================================
print("\n\n📊 TEST 3: Resumen de extracción")
print("-" * 80)

datos_clave = [
    "Customer__NAME",
    "EnergyContract__FIRMANTE_DNI",
    "EnergyContract__NAME",
    "EnergyContract__CUPS_CITY",
    "EnergyContract__COMERCIALIZADORA",
    "EnergyContract__TARIFA",
    "EnergyContract__SUMINISTRO"
]

print(f"{'Campo':<40} {'Texto':<30} {'PDF':<30}")
print("-" * 100)
for campo in datos_clave:
    valor_texto = datos.get(campo, "N/A")[:28]
    valor_pdf = datos_pdf.get(campo, "N/A")[:28]
    print(f"{campo:<40} {str(valor_texto):<30} {str(valor_pdf):<30}")

print("\n" + "=" * 80)
print("✅ PRUEBAS COMPLETADAS")
print("=" * 80)
