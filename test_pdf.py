#!/usr/bin/env python3
"""
Prueba de procesamiento de PDFs
Genera un PDF de prueba y lo procesa
"""
import json
import tempfile
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from cerebro import procesar_pdf_contrato

print("=" * 80)
print("📄 PRUEBA DE PROCESAMIENTO DE PDFs")
print("=" * 80)

# Crear un PDF de prueba realista
print("\n1️⃣ GENERANDO PDF DE PRUEBA")
print("-" * 80)

with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
    temp_pdf = tmp.name

c = canvas.Canvas(temp_pdf, pagesize=letter)
c.setFont("Helvetica-Bold", 14)
c.drawString(50, 750, "CONTRATO DE SUMINISTRO DE ENERGÍA ELÉCTRICA")
c.drawString(50, 720, "-" * 80)

y = 680
c.setFont("Helvetica-Bold", 11)
c.drawString(50, y, "1. DATOS DEL CONTRATANTE")
c.setFont("Helvetica", 10)
y -= 25
c.drawString(70, y, "Nombre Completo: María Fernanda González Sáenz")
y -= 20
c.drawString(70, y, "Documento de Identidad: 76543210D")
y -= 20
c.drawString(70, y, "Teléfono: 651234567")

y -= 40
c.setFont("Helvetica-Bold", 11)
c.drawString(50, y, "2. DATOS DEL SUMINISTRO")
c.setFont("Helvetica", 10)
y -= 25
c.drawString(70, y, "Punto de Suministro (CUPS): ES0021567401234567890EC")
y -= 20
c.drawString(70, y, "Dirección de Suministro: Calle del Carmen 78, Piso 5B")
y -= 20
c.drawString(70, y, "Código Postal: 46200")
y -= 20
c.drawString(70, y, "Municipio: Requena")
y -= 20
c.drawString(70, y, "Provincia: Valencia")

y -= 40
c.setFont("Helvetica-Bold", 11)
c.drawString(50, y, "3. CONFIGURACIÓN TÉCNICA")
c.setFont("Helvetica", 10)
y -= 25
c.drawString(70, y, "Tipo de Suministro: Electricidad")
y -= 20
c.drawString(70, y, "Comercializadora Anterior: Endesa X")
y -= 20
c.drawString(70, y, "Tarifa Contratada: 2.0A")
y -= 20
c.drawString(70, y, "Potencia Contratada: 4.6 kW")
y -= 20
c.drawString(70, y, "Tipo de Alta: Cambio de Comercializadora (CC)")

c.save()

print(f"✅ PDF generado: {temp_pdf}")
print(f"   Tamaño: {os.path.getsize(temp_pdf)} bytes")

# Procesar el PDF
print("\n2️⃣ PROCESANDO PDF CON IA")
print("-" * 80)

resultado_pdf = procesar_pdf_contrato(temp_pdf)
datos_pdf = json.loads(resultado_pdf)

print("\n✅ DATOS EXTRAÍDOS DEL PDF:")
for clave, valor in datos_pdf.items():
    if valor != "PENDIENTE":
        print(f"  ✔️  {clave}: {valor}")
    else:
        print(f"  ⚠️  {clave}: {valor}")

# Limpiar
os.remove(temp_pdf)
print(f"\n🗑️  Archivo temporal eliminado")

print("\n" + "=" * 80)
print("✅ PRUEBA DE PDF COMPLETADA")
print("=" * 80)
