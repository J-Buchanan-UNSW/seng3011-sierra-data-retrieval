import json
import os
import pandas as pd
from io import StringIO
import boto3

# Initialize S3 client
s3_client = boto3.client("s3")

# Define S3 bucket and file path
BUCKET_NAME = os.getenv("BUCKET_NAME", "dev-sierra-e-bucket")
CSV_FILE_PATH = "processedCSV/environmental_risk.csv"


def lambda_handler(event, context):
    try:
        # Log query parameters to verify they are received
        params = event.get("queryStringParameters", {}) or {}
        print("Query Parameters:", params)

        # Fetch CSV file from S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=CSV_FILE_PATH)
        csv_content = response['Body'].read().decode('utf-8')

        # Load CSV into DataFrame
        df = pd.read_csv(StringIO(csv_content))

        # Retrieve query parameters from the event
        params = event.get("queryStringParameters", {}) or {}
        filter_query = params.get("filter")
        columns = params.get("columns")
        order_by = params.get("order_by")

        # Apply filtering if a filter query is provided
        if filter_query:
            df = df.query(filter_query)

        # Select specific columns if provided
        if columns:
            col_list = [col.strip() for col in columns.split(",")]
            df = df[col_list]

        # Sort the DataFrame if an ordering is specified
        if order_by:
            order_items = order_by.split(",")
            sort_by = []
            ascending = []
            for item in order_items:
                parts = item.strip().split()
                sort_by.append(parts[0])
                # Determine ascending or descending (default ascending)
                ascending.append(False if len(parts) > 1
                                 and parts[1].lower() == "desc" else True)
            df = df.sort_values(by=sort_by, ascending=ascending)

        # Convert the resulting DataFrame to JSON
        result = df.to_json(orient="records")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": result
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
