import json
from unittest.mock import MagicMock
from lambda_functions.retrievalJSON.lambda_function import (
    lambda_handler,
    is_valid_filter_expression,
    is_valid_columns,
    is_valid_order_by
)


def parse_json_response(json_string):
    return json.loads(json_string)


def test_lambda_handler_no_params():
    # Creating sample ESG data format
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "WATERWITHDRAWALTOTAL",
                    "metric_value": "500"
                }
            }
        ]
    })

    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'application/json'

    parsed = parse_json_response(response['body'])
    assert len(parsed) == 2
    assert parsed[0]['company_name'] == 'TestCorp'
    assert parsed[0]['metric_name'] == 'CO2DIRECTSCOPE1'
    assert parsed[1]['metric_name'] == 'WATERWITHDRAWALTOTAL'


def test_lambda_handler_default_s3_client(monkeypatch):
    # Patch boto3.client to prevent real S3 call
    mock_client = MagicMock()
    monkeypatch.setattr("boto3.client", lambda service_name: mock_client)

    mock_body = MagicMock()
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            }
        ]
    })
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    response = lambda_handler(event, {})

    assert response['statusCode'] == 200


def test_lambda_handler_with_filter():
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "WATERWITHDRAWALTOTAL",
                    "metric_value": "500"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "OtherCorp",
                    "metric_name": "CO2INDIRECTSCOPE3",
                    "metric_value": "300"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "filter": "metric_value > '200'"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_json_response(response['body'])
    assert len(parsed) == 2
    assert parsed[0]['metric_value'] == '500'
    assert parsed[1]['metric_value'] == '300'


def test_lambda_handler_with_columns():
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100",
                    "metric_unit": "Tons CO2e"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "OtherCorp",
                    "metric_name": "WATERWITHDRAWALTOTAL",
                    "metric_value": "500",
                    "metric_unit": "Cubic meters"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "columns": "company_name,metric_value"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_json_response(response['body'])
    assert len(parsed) == 2
    assert 'metric_unit' not in parsed[0]
    assert 'company_name' in parsed[0]
    assert 'metric_value' in parsed[0]
    assert parsed[0]['company_name'] == 'TestCorp'
    assert parsed[1]['company_name'] == 'OtherCorp'


def test_lambda_handler_with_order():
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "AlphaCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "BetaCorp",
                    "metric_name": "WATERWITHDRAWALTOTAL",
                    "metric_value": "200"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "GammaCorp",
                    "metric_name": "CO2INDIRECTSCOPE3",
                    "metric_value": "300"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "order_by": "metric_value desc"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_json_response(response['body'])
    assert len(parsed) == 3
    assert parsed[0]['metric_value'] == '300'
    assert parsed[1]['metric_value'] == '200'
    assert parsed[2]['metric_value'] == '100'


def test_lambda_handler_all_params():
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "AlphaCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100",
                    "pillar": "E"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "BetaCorp",
                    "metric_name": "WATERWITHDRAWALTOTAL",
                    "metric_value": "200",
                    "pillar": "E"
                }
            },
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "GammaCorp",
                    "metric_name": "CO2INDIRECTSCOPE3",
                    "metric_value": "300",
                    "pillar": "E"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "filter": "metric_value > '100'",
            "columns": "company_name,metric_value",
            "order_by": "metric_value desc"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    parsed = parse_json_response(response['body'])
    assert len(parsed) == 2
    assert 'pillar' not in parsed[0]
    assert parsed[0]['metric_value'] == '300'
    assert parsed[1]['metric_value'] == '200'


def test_lambda_handler_error():
    mock_s3_client = MagicMock()
    mock_s3_client.get_object.side_effect = Exception("S3 Error")

    event = {"queryStringParameters": {}}
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 500
    assert "S3 Error" in response['body']


def test_lambda_handler_invalid_filter_param():
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
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
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
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
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
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


def test_lambda_handler_no_json_content():
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b''
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 400
    assert response['headers']['Content-Type'] == 'application/json'
    assert "No content found" in response['body']


def test_lambda_handler_no_json_content_after_filtering():
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            }
        ]
    })
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {
        "queryStringParameters": {
            "filter": "metric_value > '500'"
        }
    }
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 400
    assert response['headers']['Content-Type'] == 'application/json'
    assert "No content found" in response['body']


def test_lambda_handler_empty_dataframe_json():
    json_content = '[]'

    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    event = {"queryStringParameters": {}}
    context = {}
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    assert response['statusCode'] == 400
    assert "No content found" in response['body']


def test_lambda_handler_invalid_filter_crashes_query_json():
    json_content = json.dumps({
        "data_source": "ClarityAI_Dataset",
        "dataset_type": "Environmental_Risk",
        "dataset_id": "https://bucket-url",
        "events": [
            {
                "time_object": {"timestamp": "2023-01-01",
                                "timezone": "GMT+11"},
                "event_type": "ESG data",
                "attribute": {
                    "company_name": "TestCorp",
                    "metric_name": "CO2DIRECTSCOPE1",
                    "metric_value": "100"
                }
            }
        ]
    })

    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json_content.encode('utf-8')
    mock_s3.get_object.return_value = {'Body': mock_body}

    # Will crash df.query due to invalid filter syntax
    event = {"queryStringParameters": {"filter": "metric_value >> 100"}}
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
