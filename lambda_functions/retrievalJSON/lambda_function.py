import json
import os
import boto3
import pandas as pd


def get_s3_client():
    """
    Initialize and return an S3 client using boto3.
    """
    return boto3.client("s3")


# Define S3 bucket and file path
BUCKET_NAME = os.getenv("BUCKET_NAME", "dev-sierra-e-bucket")
JSON_FILE_PATH = "processedJSON/environmental_risk.json"

VALID_OPERATORS = {'==', '!=', '>', '<', '>=', '<='}


def is_valid_filter_expression(expr: str, valid_columns: set) -> bool:
    try:
        for op in VALID_OPERATORS:
            if op in expr:
                left, right = expr.split(op, 1)
                return left.strip() in valid_columns and right.strip() != ''
        return False
    except Exception:
        return False


def is_valid_order_by(order_by: str, valid_columns: set) -> bool:
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
    try:
        selected = [col.strip() for col in columns.split(',')]
        return all(col in valid_columns for col in selected)
    except Exception:
        return False


def lambda_handler(event, _context, s3_client=None):
    try:
        print("🚀 Starting JSON data processing...")
        print("📩 Event received:", json.dumps(event))

        # Use injected client for testing or create a new one
        if s3_client is None:
            s3_client = get_s3_client()

        print(f"📦 Fetching JSON file from s3://{BUCKET_NAME}/{JSON_FILE_PATH}")
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=JSON_FILE_PATH)
        json_content = response['Body'].read().decode('utf-8')

        if not json_content.strip():
            print("❌ JSON content is empty.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No content found"}),
                "headers": {"Content-Type": "application/json"}
            }

        try:
            parsed_json = json.loads(json_content)
            if isinstance(parsed_json, dict):
                parsed_json = [parsed_json]
            elif not isinstance(parsed_json, list):
                print("❌ Unexpected JSON structure.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid JSON structure"}),
                    "headers": {"Content-Type": "application/json"}
                }
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON: {e}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Error decoding JSON"}),
                "headers": {"Content-Type": "application/json"}
            }

        df = pd.json_normalize(parsed_json)
        print("🧾 Loaded DataFrame with {len(df)} rows" +
              f" and columns: {df.columns.tolist()}")

        if df.empty:
            print("❌ DataFrame is empty after loading JSON.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No content found"}),
                "headers": {"Content-Type": "application/json"}
            }

        valid_columns = set(df.columns)
        params = event.get("queryStringParameters", {}) or {}
        print("🔎 Received query params:", params)

        filter_query = params.get("filter")
        columns = params.get("columns")
        order_by = params.get("order_by")

        if filter_query:
            print(f"🔍 Validating filter: '{filter_query}'")
            if not is_valid_filter_expression(filter_query, valid_columns):
                print("❌ Invalid filter expression.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid filter expression"}),
                    "headers": {"Content-Type": "application/json"}
                }
            try:
                df = df.query(filter_query)
                print(f"✅ Filtered DataFrame has {len(df)} rows.")
                if df.empty:
                    print("⚠️ No results after filtering.")
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"error": "No content found"}),
                        "headers": {"Content-Type": "application/json"}
                    }
            except Exception as e:
                print(f"❌ Error applying filter: {e}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid filter expression"}),
                    "headers": {"Content-Type": "application/json"}
                }

        if columns:
            print(f"🧩 Validating requested columns: '{columns}'")
            if not is_valid_columns(columns, valid_columns):
                print("❌ Invalid columns parameter.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid columns parameter"}),
                    "headers": {"Content-Type": "application/json"}
                }
            col_list = [col.strip() for col in columns.split(",")]
            df = df[col_list]
            print(f"✅ Selected columns: {col_list}")

        if order_by:
            print(f"📐 Validating order_by: '{order_by}'")
            if not is_valid_order_by(order_by, valid_columns):
                print("❌ Invalid order_by expression.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Invalid order_by expression"}),
                    "headers": {"Content-Type": "application/json"}
                }
            order_items = order_by.split(",")
            sort_by = []
            ascending = []
            for item in order_items:
                parts = item.strip().split()
                sort_by.append(parts[0])
                if len(parts) > 1 and parts[1].lower() == "desc":
                    ascending.append(False)
                else:
                    ascending.append(True)
            df = df.sort_values(by=sort_by, ascending=ascending)
            print(f"✅ Sorted by: {sort_by} | Ascending: {ascending}")

        print(f"📤 Returning {len(df)} rows of processed data.")
        json_result = df.to_json(orient="records")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json_result
        }

    except Exception as e:
        print(f"❌ Unhandled Exception: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
