from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from evolutionapi.client import EvolutionClient
from evolutionapi.models.message import TextMessage, MediaMessage, MediaType
from io import BytesIO
import base64
from PIL import Image
from evolutionapi.models.message import ButtonMessage, Button

app = FastAPI(
    title="Vador Whapi",
    description="API para enviar mensajes de texto e imágenes a través de Evolution",
    version="0.1.0"
)

# Configuración inicial del cliente Evolution
evolution_client = EvolutionClient(
    base_url='http://vecinos.com.ar:8080',
    api_token='visiona4'
)

# Modelo para las peticiones de texto
class TextMessageRequest(BaseModel):
    number: str
    text: str
    delay: int = 0

# Función para redimensionar y convertir la imagen a Base64
def image_to_base64(file: UploadFile, width: int = None, height: int = None, upscale: bool = False) -> str:
    with Image.open(file.file) as img:
        original_width, original_height = img.size
        if width or height:
            if width and height:
                new_width, new_height = width, height
            elif width:
                new_width = width
                new_height = int((original_height * width) / original_width)
            else:
                new_height = height
                new_width = int((original_width * height) / original_height)
            if not upscale:
                new_width = min(new_width, original_width)
                new_height = min(new_height, original_height)
            img = img.resize((new_width, new_height), Image.LANCZOS)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

# 1. Listar instancias de Evolution
@app.get("/instances/")
def list_instances():
    try:
        instances = evolution_client.instances.fetch_instances()
        return instances
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Obtener estado de conexión de una instancia
@app.get("/instances/{instance_id}/status")
def get_instance_status(instance_id: str, instance_token: str):
    try:
        status = evolution_client.instance_operations.get_connection_state(
            instance_id=instance_id,
            instance_token=instance_token
        )
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Enviar mensaje de texto
@app.post("/send_text/")
def send_text_message(request: TextMessageRequest):
    try:
        instances = evolution_client.instances.fetch_instances()
        visiona_id = instances[0]['name']
        visiona_token = instances[0]['token']

        message = TextMessage(
            number=request.number,
            text=request.text,
            delay=request.delay
        )
        response = evolution_client.messages.send_text(visiona_id, message, visiona_token)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. Enviar mensaje de imagen
@app.post("/send_image/")
def send_image_message(number: str, caption: str = "", habitacion: str = "", fileName: str = "image.png", delay: int = 0, file: UploadFile = File(...)):
    responses = []
    try:
        instances = evolution_client.instances.fetch_instances()
        visiona_id = instances[0]['name']
        visiona_token = instances[0]['token']

        # Convertir la imagen a Base64
        image_b64 = image_to_base64(file, width=64, upscale=True)

        message = MediaMessage(
            number=number,
            mediatype=MediaType.IMAGE.value,
            mimetype='image/png',
            media=image_b64,
            caption=caption,
            fileName=fileName,
            delay=delay
        )

        response = evolution_client.messages.send_media(visiona_id, message, visiona_token)
        responses.append(response)


        buttons = [
            Button(
                type="reply",
                displayText="Alerta Atendida",
                id="1"
            ),
        ]
        links = [
            Button(
                type="url",
                displayText="Ver Camara",
                url="https://www.google.com",
                id="2"
            )
        ]

        mensagem = ButtonMessage(
            number=number,
            title=f"Alerta Habitacion {habitacion}",
            description="Paciente moviendose en la cama",
            footer="¿Desea atender?",
            buttons=buttons
        )

        response = evolution_client.messages.send_buttons(visiona_id, mensagem, visiona_token)
        responses.append(response)

        mensagem = ButtonMessage(
            number=number,
            title="Desea ver la camara?",
            description="",
            footer="",
            buttons=links
        )

        response = evolution_client.messages.send_buttons(visiona_id, mensagem, visiona_token)
        responses.append(response)

        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
