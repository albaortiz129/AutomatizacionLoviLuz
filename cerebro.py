import os
from datetime import datetime
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=api_key)

def analizar_consulta_loviluz(texto_cliente):
    model = "mistral-small-latest"
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    Eres el Analista Senior de Loviluz. Tu objetivo es extraer datos limpios para WolfCRM.
    DEBES devolver SOLO un JSON válido, sin texto adicional.
    
    FECHA ACTUAL: {fecha_hoy}

    INSTRUCCIONES CRÍTICAS DE LIMPIEZA:
    1. **Customer__NAME / FIRMANTE**: 
       - Extrae SOLO el nombre y apellidos completos.
       - Elimina frases como "Soy", "Me llamo", "Hola", "Mi nombre es", artículos y preposiciones.
       - Si es una empresa, extrae la Razón Social COMPLETA.
       - Formato: "NOMBRE APELLIDO1 APELLIDO2" o "RAZÓN SOCIAL EMPRESA"
       - NUNCA dejes vacío, si no encuentras, pon "PENDIENTE"
    
    2. **EnergyContract__NAME (CUPS)**: 
       - Código de 20-22 caracteres alfanuméricos.
       - Elimina espacios, puntos, guiones, saltos de línea.
       - Conviértelo SIEMPRE a MAYÚSCULAS.
       - Patrón típico: ESXXXXZZZZZZZZZZZZZZ
       - Si no encuentras CUPS exacto, pon "PENDIENTE"
    
    3. **EnergyContract__FIRMANTE_DNI**: 
       - Formato: "12345678A" (8 números + 1 letra en mayúscula) o NIE.
       - Elimina espacios, guiones, puntos.
       - Asegúrate que la letra esté en MAYÚSCULA.
       - No incluyas caracteres especiales.
       - Si no está claro, pon "PENDIENTE"
    
    4. **EnergyContract__CUPS_POSTAL_CODE**:
       - Exactamente 5 dígitos.
       - Debe ser código postal válido de España.
       - Si no está completo o es incorrecto, pon "PENDIENTE"
    
    5. **EnergyContract__CUPS_ADDRESS**:
       - Requiere: tipo vía (Calle, Avenida, Plaza, etc.) + nombre + número + piso (si aplica).
       - Elimina números de puerta incompletos sin número de piso.
       - Ejemplo correcto: "Calle Principal 10 Piso 3A" o "Avenida Madrid 42"
       - Si falta número o no está completa, pon "PENDIENTE"
    
    LÓGICA DE VALORES TÉCNICOS (NO MODIFICABLES):
    - EnergyContract__TIPO_ALTA: Detecta → "NU" (Alta nueva), "CC" (Cambio Comercializadora), "186" (Titular), "187" (Potencia), "188" (Titular+Pot), "RE" (Renovación). Sino → "PENDIENTE"
    - EnergyContract__STATUS: SIEMPRE "157"
    - EnergyContract__SUMINISTRO: Detecta tipo → "ELE" (Electricidad/Luz) o "GAS". Sino → "PENDIENTE"
    - EnergyContract__USER_ID: SIEMPRE "00411"

    MAPEO DE CAMPOS REQUERIDOS:
    - Customer__NAME: Nombre limpio del cliente.
    - EnergyContract__FIRMANTE: Nombre limpio del firmante.
    - EnergyContract__FIRMANTE_DNI: DNI/NIE del firmante.
    - EnergyContract__FIRMA_DATE: {fecha_hoy} (fecha actual o la extraída del cliente)
    - EnergyContract__NAME: CUPS validado y limpio.
    - EnergyContract__COMERCIALIZADORA: Compañía/Comercializadora actual identificada.
    - EnergyContract__CUPS_ADDRESS: Dirección completa con número de puerta.
    - EnergyContract__CUPS_POSTAL_CODE: Código postal de 5 dígitos.
    - EnergyContract__CUPS_CITY: Población/Municipio.
    - EnergyContract__CUPS_COUNTY: Provincia completa.
    - EnergyContract__DESCRIPTION: Resumen técnico corto (máx 100 caracteres).
    - EnergyContract__TIPO_ALTA: Tipo de alta detectado.
    - EnergyContract__STATUS: Estado contrato.
    - EnergyContract__SUMINISTRO: Tipo de suministro.
    - EnergyContract__USER_ID: ID usuario.

    REGLAS DE ORO:
    - Si NO encuentras un dato, DEBES poner "PENDIENTE", NO dejes vacío.
    - NO inventes datos ni hagas suposiciones.
    - Limpia TODOS los datos eliminando espacios extra, caracteres especiales innecesarios.
    - El JSON DEBE ser válido y bien formateado.
    - Mantén coherencia: si el CUPS es de GAS, EnergyContract__SUMINISTRO debe ser "GAS".

    FORMATO DE SALIDA JSON (REQUERIDO):
    {{
      "Customer__NAME": "valor",
      "EnergyContract__FIRMANTE": "valor",
      "EnergyContract__FIRMANTE_DNI": "valor",
      "EnergyContract__FIRMA_DATE": "{fecha_hoy}",
      "EnergyContract__NAME": "valor",
      "EnergyContract__COMERCIALIZADORA": "valor",
      "EnergyContract__CUPS_ADDRESS": "valor",
      "EnergyContract__CUPS_POSTAL_CODE": "valor",
      "EnergyContract__CUPS_CITY": "valor",
      "EnergyContract__CUPS_COUNTY": "valor",
      "EnergyContract__DESCRIPTION": "valor",
      "EnergyContract__TIPO_ALTA": "valor",
      "EnergyContract__STATUS": "157",
      "EnergyContract__SUMINISTRO": "valor",
      "EnergyContract__USER_ID": "00411"
    }}

    MENSAJE DEL CLIENTE: "{texto_cliente}"
    
    RESPUESTA (SOLO JSON, SIN EXPLICACIONES):
    """

    chat_response = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0  # <-- ¡AÑADE ESTO AQUÍ! (0.1 = Máxima precisión, 0 errores)
    )
    
    return chat_response.choices[0].message.content