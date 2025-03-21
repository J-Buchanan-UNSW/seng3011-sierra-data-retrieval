import csv
import json
import os
from io import StringIO

import boto3

# Initialize S3 client
s3_client = boto3.client("s3")

# Define S3 bucket and file path
BUCKET_NAME = os.getenv("BUCKET_NAME", "dev-sierra-e-bucket")
CSV_FILE_PATH = "processedCSV/environmental_risk.csv"


def lambda_handler(event, context):
    try:
        # Fetch CSV file from S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=CSV_FILE_PATH)
        csv_content = response['Body'].read().decode('utf-8')

        # Read CSV into a list of lists
        csv_reader = csv.reader(StringIO(csv_content))
        csv_data = list(csv_reader)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
                "Access-Control-Allow-Headers":
                "Content-Type, Authorization"
            },
            "body": csv_data
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
