import os
from datetime import datetime
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=api_key)

def analizar_consulta_loviluz(texto_unificado):
    model = "mistral-large-latest"
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    Eres el Analista Senior de Loviluz. Extrae datos para WolfCRM analizando MENSAJE y PDF.
    
    REGLAS OBLIGATORIAS PARA EVITAR VACÍOS:
    1. FIRMANTE: Si no se indica uno específico, usa el nombre del Titular (Customer__NAME).
    2. DNI (EnergyContract__DNI_FIRMANTE): Extrae el CIF/NIF del titular que aparezca en el PDF.
    3. FECHA: Si no hay fecha en el mensaje, usa {fecha_hoy}.
    4. TIPO_ALTA: Si mencionan 'Cambio de titular', devuelve "186".
    5. CÓDIGO CLIENTE: Busca un número de 4 dígitos en el mensaje (ej: 1025).

    FORMATO JSON (ESTRICTO):
    {{
      "Customer__NAME": "valor",
      "Customer__CODE": "valor",
      "EnergyContract__FIRMANTE": "valor",
      "EnergyContract__DNI_FIRMANTE": "valor",
      "EnergyContract__FIRMA_DATE": "{fecha_hoy}",
      "EnergyContract__NAME": "valor",
      "EnergyContract__CUPS_ADDRESS": "valor",
      "EnergyContract__CUPS_POSTAL_CODE": "valor",
      "EnergyContract__CUPS_CITY": "valor",
      "EnergyContract__CUPS_COUNTY": "valor",
      "EnergyContract__TIPO_ALTA": "valor",
      "EnergyContract__STATUS": "157",
      "EnergyContract__SUMINISTRO": "ELE o GAS",
      "EnergyContract__IBAN": "valor",
      "EnergyContract__CNAE": "valor",
      "EnergyContract__TARIFA": "valor"
    }}

    TEXTO A ANALIZAR:
    "{texto_unificado}"
    """

    chat_response = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    return chat_response.choices[0].message.content