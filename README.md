# Agente de Finanzas con LangChain y FastAPI

Este proyecto implementa un agente de IA para registrar gastos usando LangChain, FastAPI y PostgreSQL.

## Instalación

1. Clona el repositorio.
2. Crea un entorno virtual: `python -m venv .venv`
3. Activa el entorno: `source .venv/bin/activate`
4. Instala dependencias: `pip install -r requirements.txt`

## Configuración

Edita el archivo `.env` con tus credenciales:

- DB_HOST, DB_PORT, DB_NAME=n8n_db, DB_USER, DB_PASSWORD
- GOOGLE_API_KEY para Gemini

## Uso

Ejecuta el servidor: `python main.py`

Envía POST a `/webhook/` con body JSON:

```json
{
  "from": "user_id",
  "content": "Mensaje de texto",
  "mimetype": "text",
  "filename": ""
}
```

Para audio/imagen, usa base64 en `filename`.

## Funcionalidades

- Procesa texto, audio (transcripción) e imagen (OCR).
- Extrae datos de gastos: tipo, valor, categoría, fecha, descripción.
- Maneja memoria por usuario para datos faltantes.
- Inserta en BD PostgreSQL.
- Devuelve resumen o pide datos faltantes.

## Categorías

- Alimentación
- Transporte
- Entretenimiento
- Salud
- Educación
- Otros