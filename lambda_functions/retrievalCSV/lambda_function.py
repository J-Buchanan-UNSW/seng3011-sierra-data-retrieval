"""
Environmental Risk Data API Lambda Handler

This module provides an AWS Lambda function that serves environmental risk data
from a CSV file stored in S3. It supports filtering, column selection, and
sorting via query parameters.
"""

import json
import os
from io import StringIO
import boto3
import pandas as pd


def get_s3_client():
    """
    Initialize and return an S3 client using boto3.

    Returns:
        boto3.client: Configured S3 client
    """
    return boto3.client("s3")


# Define S3 bucket and file path
BUCKET_NAME = os.getenv("BUCKET_NAME", "dev-sierra-e-bucket")
CSV_FILE_PATH = "processedCSV/environmental_risk.csv"


def lambda_handler(event, _context, s3_client=None):
    """
    AWS Lambda handler function that processes requests for environmental
    risk data.

    This function retrieves a CSV file from S3, loads it into a pandas
    DataFrame,
    and applies filtering, column selection, and sorting based on query
    parameters.

    Parameters:
        event (dict): AWS Lambda event object containing query parameters
        _context (object): AWS Lambda context object (unused)
        s3_client (boto3.client, optional): S3 client for dependency injection
        during testing

    Query Parameters:
        filter (str): Pandas query expression for filtering rows
        columns (str): Comma-separated list of columns to include
        order_by (str): Comma-separated list of columns to sort by, with
        optional "desc" modifier

    Returns:
        dict: Lambda response object with status code, headers and JSON body

    Raises:
        Various exceptions that are caught and returned as 500 errors with
        error message
    """
    try:
<<<<<<< HEAD
        # Log query parameters to verify they are received
        params = event.get("queryStringParameters", {}) or {}
        print("Query Parameters:", params)
=======
        # Use injected client for testing or create a new one
        if s3_client is None:
            s3_client = get_s3_client()
>>>>>>> 592362c (Include testing for retrievalCSV)

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
