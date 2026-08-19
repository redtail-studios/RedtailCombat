"""E2E: the deployed (DEPLOYED=True) scrape pipeline — the first test in the
repo to exercise the real S3 + SQS + Lambda-worker wiring end-to-end, using
real boto3 calls against a moto-mocked AWS backend rather than faking our own
storage.py code. There is no real Lambda/EventBridge in tests, so the queue
drain + worker.handler() call below stands in for "SQS triggers the Lambda".
"""
import config
import server
import storage
import worker

YEAR = 2026
PASSWORD = server.LORE_PASSWORD


def _drain_and_process(sqs, queue_url):
    """Simulates the Lambda's SQS trigger: pull every queued message and feed
    it through the real worker.handler(), exactly the event shape SQS sends."""
    processed = 0
    while True:
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=0)
        messages = resp.get("Messages", [])
        if not messages:
            break
        event = {"Records": [{"body": m["Body"]} for m in messages]}
        worker.handler(event, None)
        for m in messages:
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=m["ReceiptHandle"])
        processed += len(messages)
    return processed


def test_deployed_scrape_through_worker_to_report(
    client, fake_scrapers, moto_aws, mock_llm,
):
    resp = client.post("/api/lore/scrape", json={"year": YEAR, "password": PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "started"
    # bucket starts empty -> nothing is "already fresh" -> every platform queued
    assert set(body["queued"]) == set(config.PLATFORM_IDS)

    processed = _drain_and_process(moto_aws["sqs"], moto_aws["queue_url"])
    assert processed == len(config.PLATFORM_IDS)

    scrape_status = client.get("/api/lore/scrape/status", params={"year": YEAR}).json()
    assert scrape_status["status"] == "done"
    assert all(v == "done" for v in scrape_status["platforms"].values())

    status = client.get("/api/lore/status").json()
    year_block = status["years"][str(YEAR)]
    assert set(year_block["sources"]) == set(config.PLATFORM_IDS)
    assert year_block["sources"]["reddit"] == len(fake_scrapers["reddit"])
    assert year_block["total"] == sum(len(v) for v in fake_scrapers.values())

    # confirm the manifest is actually reading real (moto) S3, not some
    # leftover local-mode state
    assert storage.get_cached_records(YEAR, "reddit") == fake_scrapers["reddit"]

    report_resp = client.post("/api/lore/report", json={
        "backtest_years": [YEAR], "password": PASSWORD,
    })
    assert report_resp.status_code == 200
    assert "Market Gap Analysis" in report_resp.json()["html"]


def test_scrape_enqueues_nothing_when_everything_is_already_fresh(
    client, fake_scrapers, moto_aws,
):
    first = client.post("/api/lore/scrape", json={"year": YEAR, "password": PASSWORD})
    _drain_and_process(moto_aws["sqs"], moto_aws["queue_url"])

    # every platform now has fresh (current-year, within-TTL) data in S3
    second = client.post("/api/lore/scrape", json={"year": YEAR, "password": PASSWORD})
    assert second.status_code == 200
    assert second.json() == {"status": "done", "year": YEAR, "note": "all platforms already fresh"}
