from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def leer_raiz():
    return {"status": "Servidor Loviluz Online"}

if __name__ == "__main__":
    import uvicorn
    # Ponemos el puerto 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)