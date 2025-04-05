"""
Environmental Risk Data API Lambda Handler (CSV version)

This module provides an AWS Lambda function that serves environmental risk data
from a CSV file stored in S3. It supports filtering, column selection, and
sorting via query parameters, and returns the result as CSV.
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
CSV_FILE_PATH = "processedCSV/environmental_risk.csv"

VALID_OPERATORS = {'==', '!=', '>', '<', '>=', '<='}


def is_valid_filter_expression(expr: str, valid_columns: set) -> bool:
    """
    Basic validation of a filter expression to ensure it uses valid column
    names and operators.
    """
    try:
        for op in VALID_OPERATORS:
            if op in expr:
                left, right = expr.split(op, 1)
                return left.strip() in valid_columns and right.strip() != ''
        return False
    except Exception:
        return False


def is_valid_order_by(order_by: str, valid_columns: set) -> bool:
    """
    Validates order_by expression: column [asc|desc]
    """
    try:
        for item in order_by.split(','):
            parts = item.strip().split()
            if len(parts) not in (1, 2):
                return False
            column = parts[0]
            direction = parts[1].lower() if len(parts) == 2 else 'asc'
            if column not in valid_columns or direction not in ('asc', 'desc'):
                return False
        return True
    except Exception:
        return False


def is_valid_columns(columns: str, valid_columns: set) -> bool:
    """
    Validates if all requested columns exist in the dataset.
    """
    try:
        selected = [col.strip() for col in columns.split(',')]
        return all(col in valid_columns for col in selected)
    except Exception:
        return False


def lambda_handler(event, _context, s3_client=None):
    """
    AWS Lambda handler function that processes requests for environmental
    risk data and returns it as CSV.
    """
    try:
        # Use injected client for testing or create a new one
        if s3_client is None:
            s3_client = get_s3_client()

        # Fetch CSV file from S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=CSV_FILE_PATH)
        csv_content = response['Body'].read().decode('utf-8')

        # Check if CSV content is empty
        if not csv_content.strip():
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No content found"}),
                "headers": {"Content-Type": "application/json"}
            }

        # Load CSV into DataFrame
        df = pd.read_csv(StringIO(csv_content))

        # Check if DataFrame is empty after loading
        if df.empty:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No content found"}),
                "headers": {"Content-Type": "application/json"}
            }

        # Extract valid column names from DataFrame
        valid_columns = set(df.columns)

        # Retrieve query parameters
        params = event.get("queryStringParameters", {}) or {}
        filter_query = params.get("filter")
        columns = params.get("columns")
        order_by = params.get("order_by")

        # Validate filter expression
        if filter_query and not is_valid_filter_expression(filter_query,
                                                           valid_columns):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid filter expression"}),
                "headers": {"Content-Type": "application/json"}
            }

        # Apply filter if present
        if filter_query:
            try:
                df = df.query(filter_query)
                if df.empty:
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"error": "No content found"}),
                        "headers": {"Content-Type": "application/json"}
                    }
            except Exception:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid filter expression"}),
                    "headers": {"Content-Type": "application/json"}
                }

        # Validate columns selection
        if columns and not is_valid_columns(columns, valid_columns):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid columns parameter"}),
                "headers": {"Content-Type": "application/json"}
            }

        # Select requested columns
        if columns:
            col_list = [col.strip() for col in columns.split(",")]
            df = df[col_list]

        # Validate order_by expression
        if order_by and not is_valid_order_by(order_by, valid_columns):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid order_by expression"}),
                "headers": {"Content-Type": "application/json"}
            }

        # Apply sorting if present
        if order_by:
            order_items = order_by.split(",")
            sort_by = []
            ascending = []
            for item in order_items:
                parts = item.strip().split()
                sort_by.append(parts[0])
                ascending.append(
                    False if len(parts) > 1 and parts[1].lower() == "desc"
                    else True)
            df = df.sort_values(by=sort_by, ascending=ascending)

        # Convert DataFrame to CSV (in-memory string)
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
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
