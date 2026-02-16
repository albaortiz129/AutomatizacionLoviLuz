from cerebro import analizar_consulta_loviluz

# Simulamos un mensaje real de un cliente
mensaje_prueba = """
Hola, soy Juan Pérez. Quiero cambiar mi contrato de luz a vuestra compañía. 
Mi CUPS es ES002100001234567890AA. Vivo en Madrid (28001). 
Lo quiero dejar ya firmado hoy.
"""

print("--- Iniciando prueba de IA ---")
resultado = analizar_consulta_loviluz(mensaje_prueba)
print(resultado)