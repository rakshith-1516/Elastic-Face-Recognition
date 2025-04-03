import boto3
import asyncio
import random

ASU_ID = "1229520294"
REGION = "us-east-1"
REQ_QUEUE = f"{ASU_ID}-req-queue"

MAX_INSTANCES = 15
INSTANCE_TAG_KEY = "Name"
INSTANCE_TAG_PREFIX = "app-tier-instance-"

sqs = boto3.client('sqs', region_name=REGION)
ec2 = boto3.resource('ec2', region_name=REGION)
client = boto3.client('ec2', region_name=REGION)

queue_url = sqs.get_queue_url(QueueName=REQ_QUEUE)["QueueUrl"]

idle_counter = 0  # tracks consecutive idle cycles

def get_queue_message_count():
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(attrs.get('Attributes', {}).get('ApproximateNumberOfMessages', 0))

def get_app_instances():
    instances = ec2.instances.filter(
        Filters=[{'Name': f'tag:{INSTANCE_TAG_KEY}', 'Values': [f'{INSTANCE_TAG_PREFIX}*']}]
    )
    return [i for i in instances if any(tag['Key'] == INSTANCE_TAG_KEY and tag['Value'].startswith(INSTANCE_TAG_PREFIX) for tag in i.tags or [])]

def get_stopped_instances():
    return [i for i in get_app_instances() if i.state['Name'] == 'stopped']

def get_running_instances():
    return [i for i in get_app_instances() if i.state['Name'] == 'running']

async def scale():
    global idle_counter
    pending = get_queue_message_count()
    running = get_running_instances()
    stopped = get_stopped_instances()

    print(f"[Controller] Pending Messages: {pending}, Running Instances: {len(running)}, Stopped Instances: {len(stopped)}")

    if pending <= len(running):
        idle_counter += 1
        print(f"[Controller] Idle counter: {idle_counter}")
        if idle_counter >= 2:
            # stop the extra instances
            to_stop = len(running) - pending
            if to_stop > 0:
                instance_ids = [inst.id for inst in running[:to_stop]]
                print(f"[Controller] Stopping excess instances: {instance_ids}")
                client.stop_instances(InstanceIds=instance_ids)
            idle_counter = 0  # reset after action
    else:
        # Reset idle counter on load increase
        idle_counter = 0
        to_start = min(pending - len(running), len(stopped), MAX_INSTANCES - len(running))
        if to_start > 0:
            instances_to_start = stopped[:to_start]
            instance_ids = [inst.id for inst in instances_to_start]
            print(f"[Controller] Starting instances: {instance_ids}")
            client.start_instances(InstanceIds=instance_ids)

    # Determine sleep interval
    sleep_time = 1 if pending == 0 else 0.2
    await asyncio.sleep(sleep_time + random.uniform(0, 0.5))

async def controller_loop():
    while True:
        try:
            await scale()
        except Exception as e:
            print(f"[Controller] Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(controller_loop())
