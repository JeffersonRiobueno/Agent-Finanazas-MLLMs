from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import psycopg2
import os
import base64
import tempfile
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class FinanceAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"), convert_system_message_to_human=True)
        self.memory_file = "memories.json"
        self.memories = self.load_memories()

    def load_memories(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                data = json.load(f)
                # Convertir de dict a listas de mensajes
                memories = {}
                for user, msgs in data.items():
                    memories[user] = []
                    for msg in msgs:
                        if msg['type'] == 'human':
                            memories[user].append(HumanMessage(content=msg['content']))
                        elif msg['type'] == 'ai':
                            memories[user].append(AIMessage(content=msg['content']))
                return memories
        return {}

    def save_memories(self):
        # Convertir a dict serializable
        data = {}
        for user, msgs in self.memories.items():
            data[user] = []
            for msg in msgs:
                if isinstance(msg, HumanMessage):
                    data[user].append({'type': 'human', 'content': msg.content})
                elif isinstance(msg, AIMessage):
                    data[user].append({'type': 'ai', 'content': msg.content})
        with open(self.memory_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_memory(self, user_id: str):
        if user_id not in self.memories:
            self.memories[user_id] = []
        return self.memories[user_id]

    def insert_expense(self, tipo, valor, categoria, date, descripcion):
        logger.info(f"Insertando en BD: tipo={tipo}, valor={valor}, categoria={categoria}, date={date}, descripcion={descripcion}")
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            cursor = conn.cursor()
            query = """
            INSERT INTO bot_finanzas."Data" (tipo, valor, categoria, "date", descripcion)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (tipo, valor, categoria, date, descripcion))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Inserción exitosa en BD")
            return "Gasto registrado exitosamente."
        except Exception as e:
            logger.error(f"Error insertando en BD: {str(e)}")
            return f"Error al registrar gasto: {str(e)}"

    def process_message(self, from_: str, content: str, mimetype: str, filename: str):
        print(f"Procesando mensaje para usuario {from_}: mimetype={mimetype}, content={content[:100]}...")
        logger.info(f"Procesando mensaje para usuario {from_}: mimetype={mimetype}, content={content[:100]}...")
        memory = self.get_memory(from_)
        
        if mimetype == "text":
            input_text = content
        elif mimetype.startswith("audio/ogg; codecs=opus"):
            input_text = self.transcribe_audio(content)  # Cambiar a content para audio también
        elif mimetype.startswith("image/jpeg"):
            input_text = self.extract_text_from_image(content, mimetype)  # Usar content para imagen
        else:
            print(f"Tipo de mensaje no soportado: {mimetype}")
            logger.warning(f"Tipo de mensaje no soportado: {mimetype}")
            return "Tipo de mensaje no soportado."

        # Agregar mensaje humano a memoria
        memory.append(HumanMessage(content=input_text))

        # Crear prompt con memoria
        today = datetime.now().strftime("%Y-%m-%d")
        system_prompt = f"""
        Eres un agente de finanzas. Extrae datos de gastos del mensaje proporcionado.
        Campos requeridos: tipo="gasto", valor (monto en soles, ej. 50.00), categoria (elige de: Alimentación, Transporte, Entretenimiento, Salud, Educación, Otros), date (fecha en formato YYYY-MM-DD), descripcion (breve descripción).
        Si no se menciona una fecha en el mensaje, usa la fecha actual: {today}.
        Si faltan datos, responde indicando qué datos faltan y pide que los proporcione.
        Si tienes todos los datos, responde con: "REGISTRAR: tipo=gasto, valor=X, categoria=Y, date=Z, descripcion=W"
        """
        
        messages = [SystemMessage(content=system_prompt)] + memory
        
        try:
            print(f"Enviando a LLM: {input_text}")
            logger.info(f"Enviando a LLM: {input_text}")
            response = self.llm.invoke(messages)
            ai_response = response.content
            print(f"Respuesta de LLM: {ai_response}")
            logger.info(f"Respuesta de LLM: {ai_response}")
            
            # Agregar respuesta a memoria
            memory.append(AIMessage(content=ai_response))
            
            # Verificar si es para registrar
            if ai_response.startswith("REGISTRAR:"):
                # Extraer datos y registrar
                # Parse simple: asumir formato exacto
                parts = ai_response.replace("REGISTRAR: ", "").split(", ")
                data = {}
                for part in parts:
                    key, value = part.split("=", 1)
                    data[key] = value
                
                print(f"Registrando gasto: {data}")
                logger.info(f"Registrando gasto: {data}")
                result = self.insert_expense(data['tipo'], data['valor'], data['categoria'], data['date'], data['descripcion'])
                if "exitosamente" in result:
                    final_response = f"Gasto registrado: {data['categoria']} - S/ {data['valor']} el {data['date']}. {data['descripcion']}"
                    print(f"Registro exitoso: {final_response}")
                    logger.info(f"Registro exitoso: {final_response}")
                    memory.append(AIMessage(content=final_response))
                    self.save_memories()
                    return final_response
                else:
                    print(f"Error en registro: {result}")
                    logger.error(f"Error en registro: {result}")
                    memory.append(AIMessage(content=result))
                    self.save_memories()
                    return result
            else:
                print(f"Respuesta no de registro: {ai_response}")
                logger.info(f"Respuesta no de registro: {ai_response}")
                self.save_memories()
                return ai_response
        except Exception as e:
            error_msg = f"No se pudo procesar el mensaje. Intente nuevamente o use texto. Error: {str(e)}"
            print(f"Error en process_message: {str(e)}")
            logger.error(f"Error en process_message: {str(e)}")
            memory.append(AIMessage(content=error_msg))
            self.save_memories()
            return error_msg

    def transcribe_audio(self, base64_audio: str):
        print("Transcribiendo audio...")
        logger.info("Transcribiendo audio...")
        # Validar base64
        try:
            audio_data = base64.b64decode(base64_audio)
            print(f"Base64 decodificado exitosamente, tamaño: {len(audio_data)} bytes")
            logger.info(f"Base64 decodificado exitosamente, tamaño: {len(audio_data)} bytes")
        except Exception as e:
            print(f"Error: Base64 inválido para audio: {str(e)}")
            logger.error(f"Base64 inválido para audio: {str(e)}")
            return f"Error: Base64 de audio inválido. {str(e)}"
        try:
            # Usar Google AI SDK directamente para transcripción
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            
            
            audio_data = base64.b64decode(base64_audio)
            response = model.generate_content([
                "Transcribe este audio a texto.",
                {"mime_type": "audio/ogg; codecs=opus", "data": audio_data}
            ])
            transcribed = response.text
            print(f"Transcripción obtenida: '{transcribed}'")
            logger.info(f"Transcripción obtenida: '{transcribed}'")
            
            # Validación básica
            if not transcribed or transcribed.strip() == "":
                print("Error: Transcripción vacía o inválida.")
                logger.error("Transcripción vacía o inválida.")
                return "Error: No se pudo transcribir el audio. Intente nuevamente."
            
            return transcribed
        except Exception as e:
            print(f"Error en transcripción: {str(e)}")
            logger.error(f"Error en transcripción: {str(e)}")
            return f"Error en transcripción: {str(e)}"

    def extract_text_from_image(self, base64_image: str, mimetype: str):
        print(f"Base64 image length: {len(base64_image)}, first 100: {base64_image[:100]}")
        logger.info(f"Base64 image length: {len(base64_image)}, first 100: {base64_image[:100]}")
        print("Extrayendo texto de imagen...")
        logger.info("Extrayendo texto de imagen...")
        
        # Validar base64
        try:
            image_data = base64.b64decode(base64_image)
            print(f"Base64 decodificado exitosamente, tamaño: {len(image_data)} bytes")
            logger.info(f"Base64 decodificado exitosamente, tamaño: {len(image_data)} bytes")
        except Exception as e:
            print(f"Error: Base64 inválido para imagen: {str(e)}")
            logger.error(f"Base64 inválido para imagen: {str(e)}")
            return f"Error: Base64 de imagen inválido. {str(e)}"
        
        try:
            # Usar Gemini multimodal para OCR con data URL
            from langchain_core.messages import HumanMessage
            data_url = f"data:{mimetype};base64,{base64_image}"
            message = HumanMessage(content=[
                {"type": "text", "text": "Extrae el texto de esta imagen usando OCR."},
                {"type": "image_url", "image_url": {"url": data_url}}
            ])
            response = self.llm.invoke([message])
            extracted = response.content
            print(f"Texto extraído de imagen: '{extracted}'")
            logger.info(f"Texto extraído de imagen: '{extracted}'")
            
            # Validación básica
            if not extracted or extracted.strip() == "":
                print("Error: Texto extraído vacío o inválido.")
                logger.error("Texto extraído vacío o inválido.")
                return "Error: No se pudo extraer texto de la imagen. Intente con una imagen más clara."
            
            return extracted
        except Exception as e:
            print(f"Error en OCR: {str(e)}")
            logger.error(f"Error en OCR: {str(e)}")
            return f"Error en OCR: {str(e)}"