import boto3
import json
import random
from datetime import datetime, timezone
from faker import Faker

# Initialize Faker and AWS S3 Client
fake = Faker()
s3 = boto3.client("s3")

# ⚠️ REPLACE THIS WITH YOUR EXACT S3 RAW BUCKET NAME FROM STEP 2
BUCKET_NAME = "my-elt-raw-data-bucket-uniqueid"


def generate_mock_watch_event():
    """Generates a single fake user video-watching log."""
    devices = ["mobile", "tablet", "desktop", "smart_tv"]
    return {
        "event_id": fake.uuid4(),
        "user_id": f"USER_{random.randint(100, 999)}",
        "video_id": f"VID_{random.randint(2001, 2050)}",
        "watch_time_seconds": random.randint(5, 7200),  # ranges from 5 secs to 2 hours
        "device": random.choice(devices),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    # 1. Simulate data generation (Extracting/Creating 100 rows)
    print("Generating mock video analytics data...")
    raw_events = [generate_mock_watch_event() for _ in range(100)]

    # 2. Format into JSON Lines format (highly optimal for data engineering)
    json_lines_data = "\n".join([json.dumps(e) for e in raw_events])

    # 3. Define a unique timestamped file name
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_name = f"watch_logs/raw_events_{timestamp_str}.json"

    # 4. Load/Upload directly to AWS S3 Raw Zone
    print(f"Uploading file to S3: {file_name}...")
    try:
        s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=json_lines_data)
        print("✅ Success! Raw data successfully Extracted and Loaded into S3.")
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")


if __name__ == "__main__":
    main()
