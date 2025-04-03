from flask import Flask, request, jsonify
import boto3
import threading

ASU_ID = "1229520294"
S3_BUCKET = f"{ASU_ID}-in-bucket"
SIMPLEDB_TABLE = f"{ASU_ID}-simpleDB"

s3 = boto3.client("s3", region_name="us-east-1")
simpledb = boto3.client("sdb", region_name="us-east-1")

app = Flask(__name__)

def upload_file_to_s3(file_data, file_name):
    s3.put_object(Bucket=S3_BUCKET, Key=file_name, Body=file_data)

def fetch_prediction(file_name):
    base_name = file_name.rsplit(".", 1)[0]  # Remove extension
    response = simpledb.get_attributes(
        DomainName=SIMPLEDB_TABLE, ItemName=base_name, AttributeNames=["recognition"]
    )
    return response.get("Attributes", [{}])[0].get("Value", "Unknown")

@app.route("/", methods=["POST"])
def process_request():
    uploaded_file = request.files.get("inputFile")
    if not uploaded_file:
        return jsonify({"error": "No file uploaded"}), 400

    file_name = uploaded_file.filename

    upload_thread = threading.Thread(target=upload_file_to_s3, args=(uploaded_file.read(), file_name))
    upload_thread.start()

    result = fetch_prediction(file_name)

    upload_thread.join()  # Ensure upload completes before returning response

    return f"{file_name}:{result}", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
