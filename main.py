from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from agent import FinanceAgent
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Finance Agent Webhook")

class WebhookBody(BaseModel):
    from_: str = Field(alias="from")
    content: str
    mimetype: str
    filename: str = ""

@app.post("/webhook/")
async def webhook(body: WebhookBody):
    print(f"Datos de entrada: from_={body.from_}, content={body.content}, mimetype={body.mimetype}, filename={body.filename[:50]}...")
    logger.info(f"Datos de entrada: from_={body.from_}, content={body.content}, mimetype={body.mimetype}, filename={body.filename[:50]}...")
    try:
        agent = FinanceAgent()
        response = agent.process_message(body.from_, body.content, body.mimetype, body.filename)
        print(f"Datos de salida: response={response}")
        logger.info(f"Datos de salida: response={response}")
        return {"response": response}
    except Exception as e:
        print(f"Error procesando webhook: {str(e)}")
        logger.error(f"Error procesando webhook: {str(e)}")
        return {"error": f"No se pudo procesar el mensaje. Intente nuevamente o use texto. Detalle: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)