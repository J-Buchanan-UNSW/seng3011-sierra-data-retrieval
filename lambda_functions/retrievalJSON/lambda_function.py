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
                # If it's a single object, we need to handle it differently
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

        # Create a list to store the flattened records
        flattened_records = []
        
        # Process each record in the JSON list
        for record in parsed_json:
            if "events" in record:
                # Each event needs to be flattened
                for e in record.get("events", []):
                    flat_record = {
                        "data_source": record.get("data_source", ""),
                        "dataset_type": record.get("dataset_type", ""),
                        "dataset_id": record.get("dataset_id", "")
                    }
                    # Add time_object fields if they exist
                    objects = e["time_object"].items()
                    if "time_object" in e:
                        for time_key, time_value in objects:
                            flat_record[f"time_{time_key}"] = time_value
                    # Add event_type if it exists
                    if "event_type" in e:
                        flat_record["event_type"] = e["event_type"]
                    
                    # Add attribute fields directly to the flattened record
                    if "attribute" in e:
                        for attr_key, attr_value in e["attribute"].items():
                            flat_record[attr_key] = attr_value
                    
                    flattened_records.append(flat_record)
            else:
                # Handle case where there are no events - just add the record
                flattened_records.append(record)

        # Convert to DataFrame
        df = pd.DataFrame(flattened_records)

        print(f"🧾 Loaded DataFrame with {len(df)} rows and " +
              f"columns: {df.columns.tolist()}")

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
            print("🔍 Validating filter expression...")

            if not is_valid_filter_expression(filter_query, valid_columns):
                print("❌ Invalid filter expression")
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
            if not is_valid_columns(columns, valid_columns):
                print("❌ Invalid columns")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Invalid columns expression"}),
                    "headers": {"Content-Type": "application/json"}
                }

            # Select only the specified columns
            df = df[[col.strip() for col in columns.split(",")]]

        if order_by:
            print(f"🔎 Validating and applying order_by: {order_by}")
            if not is_valid_order_by(order_by, valid_columns):
                print("❌ Invalid order_by")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Invalid order_by expression"}),
                    "headers": {"Content-Type": "application/json"}
                }

            # Process order_by parts
            order_parts = []
            ascending_flags = []
            
            for item in order_by.split(','):
                parts = item.strip().split()
                column = parts[0]
                direction = parts[1].lower() if len(parts) == 2 else 'asc'
                order_parts.append(column)
                ascending_flags.append(direction == 'asc')
            
            df = df.sort_values(by=order_parts, ascending=ascending_flags)
            print(f"✅ Sorting applied. Data sorted by {order_parts}.")

        return {
            "statusCode": 200,
            "body": df.to_json(orient="records"),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
