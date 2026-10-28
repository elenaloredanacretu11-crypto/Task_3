from app import app


def test_dashboard_page_is_served():
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Delivery Status" in response.data
    assert b"Shipment Records" in response.data


def test_summary_endpoint_includes_last_run():
    response = app.test_client().get("/api/summary")

    assert response.status_code == 200
    assert response.json["input_rows"] == 20
    assert response.json["last_run"]


def test_records_endpoint_returns_processed_shipments():
    response = app.test_client().get("/api/records")

    assert response.status_code == 200
    assert len(response.json["records"]) == 20
    assert response.json["records"][0]["order_id"] == "ORD-1001"


def test_sample_csv_can_be_downloaded_from_deployed_app():
    response = app.test_client().get("/api/download-sample")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert b"ORD-1001" in response.data
