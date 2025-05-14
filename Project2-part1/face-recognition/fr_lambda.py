import os
import json
import boto3
import torch
import numpy as np
import logging
from PIL import Image
import base64
from io import BytesIO
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = None
resnet = None
embeddings = None
queue_url = os.environ.get("QUEUE_URL")

def decode_base64_image(base64_string):
    start_time = time.time()
    image_data = base64.b64decode(base64_string)
    image = Image.open(BytesIO(image_data)).convert("RGB")
    logger.info(f"decode_base64_image took {time.time() - start_time:.4f} seconds")
    return image

def preprocess_image(image):
    start_time = time.time()
    img_array = np.asarray(image, dtype=np.float32) / 255.0
    img_array = np.transpose(img_array, (2, 0, 1))
    result = torch.tensor(img_array, dtype=torch.float32).unsqueeze(0)
    logger.info(f"preprocess_image took {time.time() - start_time:.4f} seconds")
    return result

def initialize_resources():
    global sqs, resnet, embeddings

    start_time = time.time()
    if sqs is None:
        logger.info("Initializing SQS client...")
        sqs = boto3.client("sqs", region_name="us-east-1")

    if resnet is None:
        logger.info("Loading FaceNet model...")
        resnet = torch.jit.load('resnetV1.pt').eval()
        logger.info("FaceNet model loaded.")

    if embeddings is None:
        logger.info("Loading precomputed embeddings...")
        emb_tensor, labels = torch.load('resnetV1_video_weights.pt')
        embeddings = list(zip(labels, emb_tensor))
        logger.info(f"{len(embeddings)} embeddings loaded.")

    logger.info(f"initialize_resources took {time.time() - start_time:.4f} seconds")

def handler(event, context):
    try:
        start_time = time.time()
        initialize_resources()

        batch_messages = []

        for record in event['Records']:
            body = json.loads(record['body'])
            request_id = body.get('request_id')
            filename = body.get('filename')
            face_base64 = body.get('face')

            logger.info(f"Processing request for filename: {filename}")

            image_start_time = time.time()
            image = decode_base64_image(face_base64)
            logger.info(f"Image decoding took {time.time() - image_start_time:.4f} seconds")

            preprocess_start_time = time.time()
            face_tensor = preprocess_image(image)
            logger.info(f"Image preprocessing took {time.time() - preprocess_start_time:.4f} seconds")

            embedding_start_time = time.time()
            with torch.no_grad():
                input_embedding = resnet(face_tensor)
            logger.info(f"Embedding generation took {time.time() - embedding_start_time:.4f} seconds")

            match_start_time = time.time()
            closest_match = None
            closest_distance = float('inf')

            for label, stored_embedding in embeddings:
                distance = torch.norm(input_embedding - stored_embedding).item()
                if distance < closest_distance:
                    closest_distance = distance
                    closest_match = label
            logger.info(f"Matching faces took {time.time() - match_start_time:.4f} seconds")

            logger.info(f"Prediction for {request_id}: {closest_match}")

            batch_messages.append({
                'Id': request_id,
                'MessageBody': json.dumps({
                    "request_id": request_id,
                    "result": closest_match
                })
            })

        if batch_messages:
            sqs_start_time = time.time()
            response = sqs.send_message_batch(
                QueueUrl=queue_url,
                Entries=batch_messages
            )
            logger.info(f"Sending batch to SQS took {time.time() - sqs_start_time:.4f} seconds")
            logger.info(f"Batch result sent to SQS for {len(batch_messages)} requests.")

        logger.info(f"Total handler execution time: {time.time() - start_time:.4f} seconds")
        return {'statusCode': 200, 'body': json.dumps('Face recognition complete.')}

    except Exception as e:
        logger.exception("Error during Lambda execution")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
