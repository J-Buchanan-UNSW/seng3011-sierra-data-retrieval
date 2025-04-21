import csv
import io
from unittest.mock import MagicMock
from lambda_functions.retrievalCSV.lambda_function import (
    lambda_handler,
    is_valid_filter_expression,
    is_valid_columns,
    is_valid_order_by
)


def parse_csv_response(csv_string):
    f = io.StringIO(csv_string)
    reader = csv.DictReader(f)
    return list(reader)


def test_lambda_handler_no_params():
    csv_content = 'col1,col2,col3\nval1,val2,val3\nval4,val5,val6'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'text/csv'

    parsed = parse_csv_response(response['body'])
    assert len(parsed) == 2
    assert parsed[0]['col1'] == 'val1'
    assert parsed[1]['col1'] == 'val4'


def test_lambda_handler_default_s3_client(monkeypatch):
    # Patch boto3.client to prevent real S3 call
    mock_client = MagicMock()
    monkeypatch.setattr("boto3.client", lambda service_name: mock_client)

    mock_body = MagicMock()
    csv_content = 'col1,col2,col3\nval1,val2,val3'
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    response = lambda_handler(event, {})

    assert response['statusCode'] == 200


def test_lambda_handler_with_filter():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "filter": "value > 100"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_csv_response(response['body'])
    assert len(parsed) == 2
    assert parsed[0]['value'] == '200'
    assert parsed[1]['value'] == '300'


def test_lambda_handler_with_columns():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "columns": "id,value"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_csv_response(response['body'])
    assert len(parsed) == 3
    assert 'name' not in parsed[0]
    assert parsed[0]['value'] == '100'
    assert parsed[1]['value'] == '200'
    assert parsed[2]['value'] == '300'


def test_lambda_handler_with_order():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "order_by": "value desc"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_csv_response(response['body'])
    assert len(parsed) == 3
    assert parsed[0]['value'] == '300'
    assert parsed[1]['value'] == '200'
    assert parsed[2]['value'] == '100'


def test_lambda_handler_all_params():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "filter": "value > 100",
            "columns": "id,value",
            "order_by": "value desc"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_csv_response(response['body'])
    assert len(parsed) == 2
    assert 'name' not in parsed[0]
    assert parsed[0]['value'] == '300'
    assert parsed[1]['value'] == '200'


def test_lambda_handler_error():
    mock_s3_client = MagicMock()
    mock_s3_client.get_object.side_effect = Exception("S3 Error")

    event = {"queryStringParameters": {}}
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 500
    assert "S3 Error" in response['body']


def test_lambda_handler_invalid_filter_param():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "filter": "invalid_filter"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 400
    assert response['headers']['Content-Type'] == 'application/json'
    assert "Invalid filter expression" in response['body']


def test_lambda_handler_invalid_columns_param():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "columns": "invalid_column"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 400
    assert response['headers']['Content-Type'] == 'application/json'
    assert "Invalid columns expression" in response['body']


def test_lambda_handler_invalid_order_by_param():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "order_by": "invalid_order"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 400
    assert response['headers']['Content-Type'] == 'application/json'
    assert "Invalid order_by expression" in response['body']


def test_lambda_handler_no_csv_content():
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b''
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'application/json'
    assert response['body'] == {}


def test_lambda_handler_no_csv_content_after_filtering():
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "filter": "value < 0"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'application/json'
    assert response['body'] == {}


def test_lambda_handler_empty_dataframe():
    csv_content = 'col1,col2,col3\n'
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    response = lambda_handler(event, {}, s3_client=mock_s3_client)

    assert response['statusCode'] == 200
    assert response['body'] == {}


def test_lambda_handler_invalid_filter_crashes_query():
    csv_data = "id,value\n1,100\n2,200"
    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = csv_data.encode()
    mock_s3.get_object.return_value = {'Body': mock_body}

    # Will crash df.query due to syntax error
    event = {"queryStringParameters": {"filter": "value >> 100"}}
    response = lambda_handler(event, {}, s3_client=mock_s3)
    assert response['statusCode'] == 400
    assert "Invalid filter expression" in response['body']


def test_is_valid_filter_expression_exception():
    class BadStr(str):
        def split(self, *args, **kwargs):
            raise ValueError("forced split error")

    expr = BadStr("value > 100")
    result = is_valid_filter_expression(expr, {"value"})
    assert result is False


def test_is_valid_order_by_too_many_parts():
    order_by = "column asc extra"
    valid_columns = {"column"}
    result = is_valid_order_by(order_by, valid_columns)
    assert result is False


def test_is_valid_order_by_raises_exception():
    result = is_valid_order_by(None, {"column"})
    assert result is False


def test_is_valid_columns_exception():
    result = is_valid_columns(None, {"id", "name"})
    assert result is False
