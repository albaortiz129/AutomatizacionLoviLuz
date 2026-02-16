import os
from dotenv import load_dotenv
from mistralai import Mistral

# 1. Cargamos la API Key desde el archivo .env
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
model = "mistral-large-latest"

# 2. Usamos la variable api_key (que ya tiene tu clave guardada de forma segura)
client = Mistral(api_key=api_key)

def analizar_consulta_loviluz(texto_cliente):
    prompt = f"""
    Eres el Analista de Contratación de Loviluz. Extrae los datos y devuélvelos ÚNICAMENTE en JSON.
    
    REGLAS PARA VALORES TÉCNICOS (Usa estos códigos exactos):

    - EnergyContract__TIPO_ALTA: 
        * Nueva: "NU", Renovación: "RE", Cambio de comercializadora: "CC"
        * Cambio de titular: "186", Cambio de potencia: "187", Cambio de titular y de potencia: "188"

    - EnergyContract__STATUS: 
        * Inicial/Pendiente: "157", Falta documentación: "158", Incidencia: "162"
        * Verificado: "194", En activación: "169". (VALOR POR DEFECTO: "157")

    - EnergyContract__SUMINISTRO: 
        * Electricidad: "ELE", Gas: "GAS"

    - EnergyContract__USER_ID: "00411"

    RESTO DE CAMPOS:
    - Customer__NAME: Nombre completo.
    - EnergyContract__NAME: Código CUPS.
    - EnergyContract__CUPS_CITY: Población.
    - EnergyContract__CUPS_COUNTY: Provincia.
    - EnergyContract__DESCRIPTION: Resumen con DNI y observaciones.

    IMPORTANTE: Si falta un dato, pon "PENDIENTE".
    Mensaje: "{texto_cliente}"
    """

    chat_response = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"} 
    )
    
    return chat_response.choices[0].message.content