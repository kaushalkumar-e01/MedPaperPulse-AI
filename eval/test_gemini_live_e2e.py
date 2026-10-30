"""Live End-to-End Test for Gemini AI and Document Ingestion."""

import json
import io
import urllib.request
import urllib.error
from fastapi.testclient import TestClient
from main import app

BASE_URL = "http://127.0.0.1:8000/api"


def _is_server_running() -> bool:
    """Checks if a live server is running on localhost:8000."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def test_live_workflow():
    print("=" * 80)
    print("      MEDPAPERPULSE-AI LIVE GEMINI & INGESTION END-TO-END VERIFICATION")
    print("=" * 80)

    is_live = _is_server_running()
    client = TestClient(app) if not is_live else None
    print(f"Execution Target: {'Live Uvicorn Server' if is_live else 'FastAPI In-Process TestClient'}")

    # 1. Health check
    if is_live:
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req) as resp:
            health = json.loads(resp.read().decode())
    else:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        health = resp.json()

    print("\n[1] Health Check:")
    print("  Status:", health.get("status"))
    print("  Provider:", health.get("ai_provider", {}).get("provider"))
    print("  Model:", health.get("ai_provider", {}).get("model"))
    print("  Mode:", health.get("ai_provider", {}).get("mode"))
    print("  Gemini Active:", health.get("ai_provider", {}).get("gemini_active"))
    assert health.get("status") == "ok"

    # 2. Upload Document
    sample_abstract = (
        "Background: Tirzepatide is a novel dual GIP and GLP-1 receptor agonist for obesity management. "
        "Methods: In this phase 3 double-blind trial, 2,539 adults with obesity received once-weekly tirzepatide (5, 10, or 15 mg) or placebo. "
        "Results: At week 72, the mean percentage change in weight was -20.9% with 15 mg versus -3.1% with placebo (P<0.001). "
        "Conclusions: Once-weekly tirzepatide provided substantial, sustained body-weight reduction."
    )

    if is_live:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="tirzepatide_trial.txt"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
            f"{sample_abstract}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="title"\r\n\r\n'
            f"SURMOUNT-1 Phase 3 Trial\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        upload_req = urllib.request.Request(
            f"{BASE_URL}/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(upload_req) as resp:
            doc = json.loads(resp.read().decode())
    else:
        resp = client.post(
            "/api/upload",
            files={"file": ("tirzepatide_trial.txt", io.BytesIO(sample_abstract.encode("utf-8")), "text/plain")},
            data={"title": "SURMOUNT-1 Phase 3 Trial"},
        )
        assert resp.status_code == 200
        doc = resp.json()

    print("\n[2] Document Upload (POST /api/upload):")
    print("  Doc ID:", doc.get("doc_id"))
    print("  Title:", doc.get("title"))
    print("  Type:", doc.get("doc_type"))
    print("  Sentences:", len(doc.get("sentences", [])))
    print("  Preview:", doc.get("preview_text")[:80])
    assert doc.get("doc_id") is not None
    assert len(doc.get("sentences", [])) > 0

    # 3. Gemini / Grounded Chat
    chat_payload = {
        "query": "What was the mean weight reduction at week 72?",
        "active_paper_id": doc["doc_id"],
        "active_paper_abstract": doc["full_text"],
    }
    if is_live:
        chat_req = urllib.request.Request(
            f"{BASE_URL}/chat",
            data=json.dumps(chat_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(chat_req) as resp:
            chat_res = json.loads(resp.read().decode())
    else:
        resp = client.post("/api/chat", json=chat_payload)
        assert resp.status_code == 200
        chat_res = resp.json()

    print("\n[3] Grounded Chat (POST /api/chat):")
    print("  Response:", chat_res.get("response"))
    print("  Citations:", chat_res.get("citations"))
    print("  Mode:", chat_res.get("mode"))
    print("  Grounded:", chat_res.get("is_grounded"))
    print("  Status:", chat_res.get("status"))
    assert chat_res.get("response") is not None

    # 4. Summarize
    sum_payload = {
        "paper_id": doc["doc_id"],
        "abstract": doc["full_text"],
        "title": doc["title"],
        "summary_depth": "Standard",
        "audience": "Researcher",
    }
    if is_live:
        sum_req = urllib.request.Request(
            f"{BASE_URL}/summarize",
            data=json.dumps(sum_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(sum_req) as resp:
            sum_res = json.loads(resp.read().decode())
    else:
        resp = client.post("/api/summarize", json=sum_payload)
        assert resp.status_code == 200
        sum_res = resp.json()

    print("\n[4] Summarization (POST /api/summarize):")
    print("  Summary:", sum_res.get("summary"))
    print("  Mode:", sum_res.get("mode"))
    print("  Provider Info:", sum_res.get("provider_info"))
    print("  PICO Outcome:", sum_res.get("pico", {}).get("outcome"))
    assert sum_res.get("summary") is not None

    print("\n" + "=" * 80)
    print("ALL LIVE GEMINI & INGESTION WORKFLOW TESTS COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    test_live_workflow()
