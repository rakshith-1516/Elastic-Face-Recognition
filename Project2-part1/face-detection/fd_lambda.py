import base64
import json
import boto3
import os
import io
import logging
from PIL import Image
from facenet_pytorch import MTCNN
import torch

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = None
mtcnn = None
queue_url = os.environ.get("QUEUE_URL")

logger.info("Starting fd_lambda.py ...")

def handler(event, context):
    global sqs, mtcnn, queue_url

    try:
        if sqs is None:
            logger.info("Initializing SQS client...")
            sqs = boto3.client("sqs", region_name="us-east-1")

        if mtcnn is None:
            logger.info("Initializing MTCNN...")
            mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20)

        body = json.loads(event.get('body', '{}'))
        image_b64 = body['content']
        request_id = body['request_id']
        filename = body['filename']

        logger.info(f"Processing request_id={request_id}, filename={filename}")

        image_bytes = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

        face = mtcnn(image, return_prob=False, save_path=None)

        encoded_face = None
        if face is not None:
            face_img = face - face.min()
            face_img = face_img / face_img.max()
            face_img = (face_img * 255).byte().permute(1, 2, 0).numpy()
            face_pil = Image.fromarray(face_img, mode="RGB")

            buffer = io.BytesIO()
            face_pil.save(buffer, format="JPEG")
            encoded_face = base64.b64encode(buffer.getvalue()).decode('utf-8')
            logger.info(f"Detected face...")

        else:
            logger.info("No face detected.")

        message = {
            'request_id': request_id,
            'filename': filename,
            'face': encoded_face
        }

        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )

        logger.info(f"Message sent to SQS. Message ID: {response['MessageId']}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Face detection complete"
            })
        }

    except Exception as e:
        logger.exception("Unhandled exception in Lambda handler")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
