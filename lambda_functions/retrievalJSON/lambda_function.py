import json
import boto3

# Initialize AWS S3 client
s3_client = boto3.client("s3")

# Define S3 bucket and JSON file path
BUCKET_NAME = "sierra-e-bucket"
JSON_FILE_PATH = "processedJSON/environmental_risk.json"

def lambda_handler(event, context):
    try:
        # Fetch JSON file from S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=JSON_FILE_PATH)
        json_data = response['Body'].read().decode('utf-8')

        parsed_json = json.loads(json_data)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": parsed_json
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
