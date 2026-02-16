import google.generativeai as genai
import os
from dotenv import load_dotenv

# Cargamos la clave del archivo .env
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash')

def analizar_consulta_loviluz(texto_cliente):
    prompt = f"""
    Actúa como un experto en iluminación de la empresa Loviluz. 
    Analiza el siguiente mensaje y devuelve un resumen muy corto:
    Mensaje: "{texto_cliente}"
    """
    response = model.generate_content(prompt)
    return response.text