# Elastic Face Recognition Application

## Project Overview
This project involves developing an elastic face recognition application on AWS using machine learning for face recognition and autoscaling for dynamic resource allocation. The architecture includes a web tier, an application tier, and a custom autoscaling controller.

## Architecture

### Web Tier
- Handles HTTP POST requests on port 8000 with image uploads.
- Stores uploaded images in an S3 input bucket.
- Sends requests to the SQS request queue.
- Returns face recognition results in plain text (e.g., `filename:prediction`) after receiving the results from the SQS response queue.

### Application Tier
- Processes face recognition using a deep learning model.
- Fetches images from the S3 input bucket and stores results in the S3 output bucket.
- Pushes recognition results to the SQS response queue.

### Autoscaling
- Custom autoscaling algorithm scales the application tier based on the request queue.
- Scales up to 15 instances and scales down when there are no pending requests.

## Setup

### Prerequisites
- AWS account with EC2, S3, and SQS access.
- Python 3.x and required libraries (`Flask`, `boto3`, `torch`, etc.).
- AWS CLI configured.

### Instructions
1. **Web Tier**: 
   - Run `server.py` to start the web server.
   - Handles image uploads and communication with the app tier.

2. **Application Tier**:
   - Set up EC2 with deep learning model and required packages.
   - Implement logic in `backend.py` to process images and return results.

3. **Autoscaling**:
   - Implement autoscaling logic in `controller.py` to manage application tier instances.

4. **S3 & SQS**:
   - Create S3 buckets: `<ASU ID>-in-bucket`, `<ASU ID>-out-bucket`.
   - Create SQS queues: `<ASU ID>-req-queue`, `<ASU ID>-resp-queue`.

## Example Usage
1. Upload an image via HTTP POST.
2. The web tier processes and stores the image in S3.
3. The app tier processes the image and stores results in S3.
4. The web tier retrieves and returns the result (e.g., `test_000:Paul`).

## Naming Conventions
- S3 Buckets: `<ASU ID>-in-bucket`, `<ASU ID>-out-bucket`.
- SQS Queues: `<ASU ID>-req-queue`, `<ASU ID>-resp-queue`.
- EC2 Instances: `web-instance`, `app-tier-instance-<instance#>`.

## Conclusion
This project utilizes AWS cloud resources to create a scalable face recognition application, incorporating autoscaling and machine learning for real-time processing.

