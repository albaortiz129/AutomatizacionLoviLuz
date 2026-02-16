import google.generativeai as genai
import os
from dotenv import load_dotenv

# Cargamos la clave del archivo .env
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash')

def analizar_consulta_loviluz(texto_cliente):
    """
    Analiza el mensaje del cliente y devuelve un JSON mapeado directamente
    a los IDs y Values técnicos de WolfCRM.
    """
    
    prompt = f"""
    Eres el Analista de Contratación de Loviluz. Extrae la información del mensaje y devuélvela ÚNICAMENTE en formato JSON.
    
    REGLAS PARA VALORES TÉCNICOS (Usa estos códigos exactos de los desplegables):

    1. EnergyContract__TIPO_ALTA (Basado en tus capturas):
       - Si es Nueva: "NU"
       - Si es Renovación: "RE"
       - Si es Cambio de comercializadora: "CC"
       - Si es Cambio de titular: "186"
       - Si es Cambio de potencia: "187"
       - Si es Cambio de titular y de potencia: "188"

    2. EnergyContract__STATUS (Códigos de estado inspeccionados):
       - Pendiente inicial: "157"
       - Falta documentación: "158"
       - Incidencia: "162"
       - Verificado: "194"
       - En activación: "169"
       - En trámite: "161"
       - VALOR POR DEFECTO: "157"

    3. EnergyContract__SUMINISTRO:
       - Si es Electricidad: "ELE"
       - Si es Gas: "GAS"

    4. DATOS FIJOS:
       - EnergyContract__USER_ID: "00411"

    5. EXTRACCIÓN DE TEXTO:
       - Customer__NAME: Nombre completo o Razón Social.
       - EnergyContract__NAME: Código CUPS completo.
       - EnergyContract__CUPS_CITY: Población.
       - EnergyContract__CUPS_COUNTY: Provincia.
       - EnergyContract__DESCRIPTION: Resumen técnico (incluye DNI, teléfono y tarifa si aparecen).

    IMPORTANTE: 
    - Si un dato no aparece, pon "PENDIENTE".
    - Responde solo con el objeto JSON, sin texto adicional.

    Mensaje del cliente: "{texto_cliente}"
    """
    
    # Configuración para asegurar que la salida sea un JSON puro
    response = model.generate_content(
        prompt, 
        generation_config={
            "response_mime_type": "application/json"
        }
    )
    
    return response.text