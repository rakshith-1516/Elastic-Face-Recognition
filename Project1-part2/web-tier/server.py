from flask import Flask, request
import boto3
import threading
import time

ASU_ID = "1229520294"
S3_BUCKET = f"{ASU_ID}-in-bucket"
REQ_QUEUE = f"{ASU_ID}-req-queue"
RESP_QUEUE = f"{ASU_ID}-resp-queue"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)
sqs = boto3.client("sqs", region_name=REGION)

req_queue_url = sqs.get_queue_url(QueueName=REQ_QUEUE)["QueueUrl"]
resp_queue_url = sqs.get_queue_url(QueueName=RESP_QUEUE)["QueueUrl"]

app = Flask(__name__)

# Shared map and condition lock
response_map = {}
response_lock = threading.Lock()
response_condition = threading.Condition(lock=response_lock)

def upload_file_to_s3(file_data, file_name):
    s3.put_object(Bucket=S3_BUCKET, Key=file_name, Body=file_data)

def send_message_to_request_queue(file_name):
    sqs.send_message(QueueUrl=req_queue_url, MessageBody=file_name)

def response_consumer():
    print("[Consumer Thread] Started listening for responses...")
    while True:
        messages = sqs.receive_message(
            QueueUrl=resp_queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=10
        ).get("Messages", [])

        if not messages:
            continue

        with response_lock:
            for message in messages:
                body = message["Body"]
                print(f"[Consumer Thread] Message received: {body}")
                # Expect format: "filename:result"
                if ":" in body:
                    file_prefix = body.split(":")[0]
                    response_map[file_prefix] = body
                    print(response_map)

                    # Notify any waiting thread
                    response_condition.notify_all()

                # Remove message from SQS
                sqs.delete_message(
                    QueueUrl=resp_queue_url,
                    ReceiptHandle=message["ReceiptHandle"]
                )

# Start the background response listener
listener_thread = threading.Thread(target=response_consumer, daemon=True)
listener_thread.start()

@app.route("/", methods=["POST"])
def process_request():
    uploaded_file = request.files.get("inputFile")
    if not uploaded_file:
        return "No file uploaded", 400

    file_name = uploaded_file.filename

    upload_thread = threading.Thread(target=upload_file_to_s3, args=(uploaded_file.read(), file_name))
    upload_thread.start()

    send_message_to_request_queue(file_name)
    print("[App] Message sent to request queue")

    file_name = file_name.split(".")[0]
    print(f"Filename: {file_name}")

    upload_thread.join()

    # Wait for result in shared map
    start_time = time.time()
    timeout = 120
    result = None

    with response_lock:
        while True:
            if file_name in response_map:
                result = response_map.pop(file_name)
                break

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                result = f"{file_name}:Timeout"
                break

            response_condition.wait(timeout=5)

    print(result)
    return result, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
