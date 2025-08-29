from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import Response
import os

# importa tu función de conversión
from sii_xml_pdf.renderer import render_pdf_from_xml  

API_TOKEN = os.getenv("API_TOKEN", "change_me")
MAX_XML_SIZE = int(os.getenv("MAX_XML_SIZE", "1048576"))  # 1MB

app = FastAPI(title="SII XML→PDF Service", version="1.0.0")

def check_auth(authorization: str):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/render")
async def render(authorization: str = Header(None),
                 file: UploadFile = File(...)):
    # Autenticación
    check_auth(authorization)

    # Leer XML
    data = await file.read()
    if len(data) > MAX_XML_SIZE:
        raise HTTPException(status_code=413, detail="XML too large")

    # Generar PDF en memoria
    try:
        pdf_bytes = render_pdf_from_xml(data)
        if not pdf_bytes.startswith(b"%PDF"):
            raise RuntimeError("Invalid PDF generated")
        return Response(pdf_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
