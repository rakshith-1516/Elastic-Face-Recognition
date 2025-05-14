# Elastic Face Recognition Application

An elastic and scalable face recognition system designed using a microservices and serverless architecture. This project is implemented in **four phases**, progressively incorporating AWS services like **EC2, S3, SQS, Lambda, ECR, Greengrass**, and **MQTT** for edge computing.

---

## 📁 Project Structure

### Phase 1: Web & Application Tiers

#### 📌 Project 1 - Part 1: Web Tier

This phase builds the web front-end of the application.

- Listens for HTTP `POST` requests on **port 8000**.
- Accepts image file uploads via HTTP.
- Uploads images to an **S3 Input Bucket**.
- Publishes a message to the **SQS Request Queue**.
- Waits for a response on the **SQS Response Queue**.
- Responds with face recognition results in plain text: **filename: prediction**


#### 📌 Project 1 - Part 2: Application Tier & Autoscaling

This phase implements the face recognition backend with dynamic scaling.

- Polls the **SQS Request Queue** for tasks.
- Downloads images from the **S3 Input Bucket**.
- Runs **deep learning-based face recognition**.
- Uploads results to the **S3 Output Bucket**.
- Sends results to the **SQS Response Queue**.
- Implements **custom autoscaling logic**:
- Scales **up to 15 EC2 instances** based on queue depth.
- Scales **down to zero** when idle.

---

### Phase 2: Serverless and Edge Enhancements

#### 📌 Project 2 - Part 1: Serverless Lambda Architecture

Refactors backend processing using AWS Lambda.

- Dockerized **face detection** and **recognition** logic.
- Packaged and uploaded to **AWS ECR**.
- Lambda functions created from ECR images.
- Retains original message passing and S3 storage architecture.

#### 📌 Project 2 - Part 2: Edge Computing with AWS Greengrass

Moves detection closer to the source using edge devices.

- Face **detection performed at the edge** using **AWS Greengrass**.
- Results and images are published to cloud using **MQTT Pub/Sub**.
- Face **recognition happens in the cloud** using AWS Lambda or EC2 tier.
- Reduces latency and cloud bandwidth usage.

---

## 🧰 Technologies Used

- **AWS S3** – Image storage
- **AWS SQS** – Asynchronous message queues
- **AWS EC2** – Scalable backend compute
- **AWS Lambda** – Serverless processing
- **AWS ECR** – Container image storage for Lambda
- **AWS Greengrass** – Edge runtime for IoT
- **MQTT** – Lightweight messaging for edge-cloud communication
- **Docker** – Containerization
- **Python** – Backend and inference logic
- **Flask** – HTTP Web server

---

## 🚀 Getting Started

1. **Web Tier**:
- Run Flask server on port 8000.
- Set up AWS credentials and configure S3 and SQS.

2. **Application Tier**:
- Launch EC2 instances with prebuilt AMIs.
- Deploy autoscaling logic (CloudWatch, scripts, etc.).

3. **Serverless Setup**:
- Build and push Docker images to AWS ECR.
- Deploy Lambda functions from ECR images.

4. **Edge Setup**:
- Set up AWS Greengrass core on the edge device.
- Deploy face detection model and MQTT connectors.

---

## 📈 Scalability

- Application tier scales dynamically
- Lambda functions enable near-unlimited concurrency.
- Edge processing reduces cloud workload, ideal for IoT setups.

---

## 🧪 Sample Output

```text
image_01.jpg: face detected - John Doe
image_02.jpg: face not recognized
image_03.jpg: face detected - Jane Smith