import base64
import json
import boto3
import io
import logging
import threading
from PIL import Image
import numpy as np
from facenet_pytorch import MTCNN

from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import (
    SubscribeToIoTCoreRequest,
    QOS,
    BinaryMessage
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ipc_client = GreengrassCoreIPCClientV2()
sqs = boto3.client("sqs", region_name="us-east-1")
request_queue_url = "https://sqs.us-east-1.amazonaws.com/402978265179/1229520294-req-queue"
response_queue_url = "https://sqs.us-east-1.amazonaws.com/402978265179/1229520294-resp-queue"
mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20, post_process=True)

topic_name = "clients/1229520294-IoTThing"

class StreamHandler:
    def __init__(self):
        pass

    def on_stream_event(self, event: BinaryMessage):
        try:
            payload = event.message.payload
            message_str = payload.decode('utf-8')
            message_json = json.loads(message_str)
            logger.info(f"Received MQTT message - request_id: {message_json['request_id']}, filename: {message_json['filename']}")

            image_b64 = message_json['encoded']
            request_id = message_json['request_id']
            filename = message_json['filename']

            image_bytes = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

            faces = mtcnn.detect(image)

            if faces[0] is not None and len(faces[0]) > 0:
                for face in faces[0]:
                    x1, y1, x2, y2 = [int(coord) for coord in face]
                    face_img = image.crop((x1, y1, x2, y2))

                    face_array = np.array(face_img)

                    face_img = face_array - face_array.min()
                    face_img = face_img / face_img.max()

                    face_img = (face_img * 255).astype(np.uint8)

                    face_pil = Image.fromarray(face_img, mode="RGB")

                    face_pil = face_pil.resize((240, 240))

                    buffer = io.BytesIO()
                    face_pil.save(buffer, format="JPEG")
                    encoded_face = base64.b64encode(buffer.getvalue()).decode('utf-8')

                    logger.info("Face detected and encoded.")

                    response = sqs.send_message(
                        QueueUrl=request_queue_url,
                        MessageBody=json.dumps({
                            'request_id': request_id,
                            'filename': filename,
                            'face': encoded_face
                        })
                    )
                    logger.info(f"Sent message to Request Queue: {request_id} : {response['MessageId']}")

            else:
                logger.info("No face detected.")

                response = sqs.send_message(
                    QueueUrl=response_queue_url,
                    MessageBody=json.dumps({
                        'request_id': request_id,
                        'filename': filename,
                        'result': 'No-Face'
                    })
                )
                logger.info(f"Sent message to Response Queue: {request_id} : {response['MessageId']}")

        except Exception as e:
            logger.exception(f"Error processing MQTT message: {e}")

    def on_stream_error(self, error):
        logger.error(f"Stream error: {error}")
        return True

    def on_stream_closed(self):
        logger.info("MQTT stream closed.")

def main():
    try:
        logger.info(f"Subscribing to topic {topic_name}...")

        request = SubscribeToIoTCoreRequest()
        request.topic_name = topic_name
        request.qos = QOS.AT_LEAST_ONCE

        handler = StreamHandler()

        def subscribe_to_iot_core():
            ipc_client.subscribe_to_iot_core(
                topic_name=topic_name,
                qos=QOS.AT_LEAST_ONCE,
                on_stream_event=handler.on_stream_event,
                on_stream_error=handler.on_stream_error,
                on_stream_closed=handler.on_stream_closed
            )

        subscription_thread = threading.Thread(target=subscribe_to_iot_core)
        subscription_thread.daemon = True
        subscription_thread.start()

        logger.info("Subscribed successfully. Waiting for messages...")

        event = threading.Event()
        event.wait()

    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")

if __name__ == '__main__':
    main()
