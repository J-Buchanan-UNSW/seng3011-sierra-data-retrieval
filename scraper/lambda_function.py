"""
This file has not been deployed, but rather shows our working scraper's code.
"""

import json
import os
from io import StringIO
import boto3
import pandas as pd


def get_s3_client():
    """
    Initialize and return an S3 client using boto3.
    """
    return boto3.client("s3")


# Define S3 bucket and file path
BUCKET_NAME = os.getenv("BUCKET_NAME", "dev-sierra-e-bucket")
CSV_FILE_PATH = "esgScoreCSV/CompanyScores.csv"


def lambda_handler(event, _context, s3_client=None):
    try:
        print("🚀 Starting CSV data processing...")
        print("📩 Event received:", json.dumps(event))

        # Use injected client for testing or create a new one
        if s3_client is None:
            s3_client = get_s3_client()

        print(f"📦 Fetching CSV file from s3://{BUCKET_NAME}/{CSV_FILE_PATH}")
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=CSV_FILE_PATH)
        csv_content = response['Body'].read().decode('utf-8')

        if not csv_content.strip():
            print("❌ CSV content is empty.")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods":
                    "OPTIONS, GET, POST",
                    "Access-Control-Allow-Headers":
                    "Content-Type, Authorization"
                },
                "body": json.dumps({"status": "No content found"})
            }

        df = pd.read_csv(StringIO(csv_content))
        output = StringIO()
        df.to_csv(output, index=False)
        csv_result = output.getvalue()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/csv",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": csv_result
        }

    except Exception as e:
        print(f"❌ Unhandled Exception: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
