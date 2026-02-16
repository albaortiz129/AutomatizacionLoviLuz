import os
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")

client = Mistral(api_key=api_key)

def analizar_consulta_loviluz(texto_cliente):
    model = "mistral-small-latest"
    
    prompt = f"""
    Eres el Analista de Loviluz. Extrae los datos y devuélvelos ÚNICAMENTE en JSON puro.
    
    REGLAS DE VALORES (Usa estos códigos exactos):
    - EnergyContract__TIPO_ALTA: Nueva: "NU", Renovación: "RE", Cambio de comercializadora: "CC", Cambio de titular: "186", Cambio de potencia: "187", Cambio de titular y potencia: "188"
    - EnergyContract__STATUS: "157"
    - EnergyContract__SUMINISTRO: Electricidad: "ELE", Gas: "GAS"
    - EnergyContract__USER_ID: "00411"

    CAMPOS DE TEXTO:
    - Customer__NAME: Nombre completo
    - EnergyContract__NAME: CUPS
    - EnergyContract__CUPS_CITY: Población
    - EnergyContract__CUPS_COUNTY: Provincia
    - EnergyContract__DESCRIPTION: Resumen con DNI y observaciones

    IMPORTANTE: Si falta un dato, pon "PENDIENTE".
    Mensaje: "{texto_cliente}"
    """

    chat_response = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"} 
    )
    
    return chat_response.choices[0].message.content