import boto3
import os
import sys
import asyncio
import signal
from functools import partial

sys.path.append('/home/ec2-user/CSE546-SPRING-2025-model')
from face_recognition import face_match

ASU_ID = '1229520294'
REGION = 'us-east-1'

sqs = boto3.client('sqs', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

request_queue_url = sqs.get_queue_url(QueueName=f'{ASU_ID}-req-queue')['QueueUrl']
response_queue_url = sqs.get_queue_url(QueueName=f'{ASU_ID}-resp-queue')['QueueUrl']

input_bucket = f'{ASU_ID}-in-bucket'
output_bucket = f'{ASU_ID}-out-bucket'

shutdown_flag = False

def handle_shutdown(signum, frame):
    global shutdown_flag
    print("Shutdown signal received. Finishing current task then exiting...")
    shutdown_flag = True

signal.signal(signal.SIGTERM, handle_shutdown)

async def receive_message_async():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(
        sqs.receive_message,
        QueueUrl=request_queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    ))

async def download_from_s3_async(key, local_path):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(s3.download_file, input_bucket, key, local_path))

async def upload_to_s3_async(key, content):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(
        s3.put_object,
        Bucket=output_bucket,
        Key=key,
        Body=content.encode('utf-8')
    ))

async def send_message_async(message):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(
        sqs.send_message,
        QueueUrl=response_queue_url,
        MessageBody=message
    ))

async def delete_message_async(receipt_handle):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(
        sqs.delete_message,
        QueueUrl=request_queue_url,
        ReceiptHandle=receipt_handle
    ))

async def process_request():
    response = await receive_message_async()
    if 'Messages' not in response:
        print("No messages in queue.")
        return

    message = response['Messages'][0]
    receipt_handle = message['ReceiptHandle']
    image_key = message['Body']

    print(f"Received image request: {image_key}")
    local_image_path = f'/tmp/{image_key}'

    await download_from_s3_async(image_key, local_image_path)

    pred_name, pred_prob = face_match(local_image_path, '/home/ec2-user/CSE546-SPRING-2025-model/data.pt')

    result_key = os.path.splitext(image_key)[0]
    result_message = f"{result_key}:{pred_name}"

    await upload_to_s3_async(result_key, pred_name)
    print(f"Stored prediction '{pred_name}' in output bucket under key '{result_key}'")

    await send_message_async(result_message)
    print(f"Sent result to response queue: {result_message}")

    await delete_message_async(receipt_handle)
    print("Deleted message from request queue.")

async def worker_loop():
    while not shutdown_flag:
        await process_request()
        await asyncio.sleep(1)

    print("Worker exiting gracefully.")

if __name__ == "__main__":
    asyncio.run(worker_loop())
