from fastapi import FastAPI, Request
from cerebro import analizar_consulta_loviluz # Importamos el trabajo del Socio B
import uvicorn

app = FastAPI()

@app.post("/analizar")
async def handle_request(request: Request):
    # 1. Recibimos los datos que mande el CRM (o nosotros probando)
    datos = await request.json()
    mensaje = datos.get("mensaje", "Sin mensaje")
    
    # 2. Se lo pasamos a la IA
    resultado_ia = analizar_consulta_loviluz(mensaje)
    
    # 3. Respondemos con el análisis
    return {
        "status": "procesado",
        "analisis_ia": resultado_ia
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)