import json
import os
import boto3
import pandas as pd


def get_s3_client():
    return boto3.client("s3")


BUCKET_NAME = os.getenv("BUCKET_NAME", "dev-sierra-e-bucket")
JSON_FILE_PATH = "processedJSON/master.json"
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
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "No content found"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
                    "Access-Control-Allow-Headers":
                    "Content-Type, Authorization"
                },
            }

        try:
            parsed_json = json.loads(json_content)
            if isinstance(parsed_json, dict):
                parsed_json = [parsed_json]
            elif not isinstance(parsed_json, list):
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid JSON structure"}),
                    "headers": {"Content-Type": "application/json"}
                }
        except json.JSONDecodeError as e:
            print(e)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Error decoding JSON"}),
                "headers": {"Content-Type": "application/json"}
            }

        flattened_records = []

        for record in parsed_json:
            if "events" in record:
                for e in record.get("events", []):
                    flat_record = {
                        "data_source": record.get("data_source", ""),
                        "dataset_type": record.get("dataset_type", ""),
                        "dataset_id": record.get("dataset_id", "")
                    }
                    if "time_object" in e:
                        for time_key, time_value in e["time_object"].items():
                            flat_record[f"time_{time_key}"] = time_value
                    if "event_type" in e:
                        flat_record["event_type"] = e["event_type"]
                    if "attribute" in e:
                        for attr_key, attr_value in e["attribute"].items():
                            flat_record[attr_key] = attr_value
                    flattened_records.append(flat_record)
            else:
                flattened_records.append(record)

        df = pd.DataFrame(flattened_records)

        if df.empty:
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "No content found"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
                    "Access-Control-Allow-Headers":
                    "Content-Type, Authorization"
                },
            }

        valid_columns = set(df.columns)
        params = event.get("queryStringParameters", {}) or {}

        filter_query = params.get("filter")
        columns = params.get("columns")
        order_by = params.get("order_by")

        # Pagination params
        try:
            page = max(1, int(params.get("page", 1)))
            page_size = max(1, int(params.get("page_size", 100)))
        except ValueError:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid pagination parameters"}),
                "headers": {"Content-Type": "application/json"}
            }

        if filter_query:
            if not is_valid_filter_expression(filter_query, valid_columns):
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid filter expression"}),
                    "headers": {"Content-Type": "application/json"}
                }
            try:
                df = df.query(filter_query)
                if df.empty:
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"status": "No content found"}),
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods":
                            "OPTIONS, GET, POST",
                            "Access-Control-Allow-Headers":
                            "Content-Type, Authorization"
                        },
                    }
            except Exception as e:
                print(e)
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid filter expression"}),
                    "headers": {"Content-Type": "application/json"}
                }

        if columns:
            if not is_valid_columns(columns, valid_columns):
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Invalid columns expression"}),
                    "headers": {"Content-Type": "application/json"}
                }
            df = df[[col.strip() for col in columns.split(",")]]

        if order_by:
            if not is_valid_order_by(order_by, valid_columns):
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Invalid order_by expression"}),
                    "headers": {"Content-Type": "application/json"}
                }

            order_parts = []
            ascending_flags = []

            for item in order_by.split(','):
                parts = item.strip().split()
                column = parts[0]
                direction = parts[1].lower() if len(parts) == 2 else 'asc'
                order_parts.append(column)
                ascending_flags.append(direction == 'asc')

            df = df.sort_values(by=order_parts, ascending=ascending_flags)

        # Apply pagination
        total_records = len(df)
        total_pages = (total_records + page_size - 1) // page_size

        if page > total_pages:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Page number out of range"}),
                "headers": {"Content-Type": "application/json"}
            }

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_df = df.iloc[start_idx:end_idx]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": total_pages,
                "data": json.loads(paginated_df.to_json(orient="records"))
            }),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
