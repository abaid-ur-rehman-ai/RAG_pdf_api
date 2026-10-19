import io
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from main import app
from pypdf import PdfReader, PdfWriter

reader = PdfReader("Road map.pdf")
writer = PdfWriter()
for i in range(2):
    writer.add_page(reader.pages[i])

with open("test/sample.pdf", "wb") as f:
    writer.write(f)

client = TestClient(app)

SAMPLE = Path(__file__).parent / "sample.pdf"


def make_blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_normal_question():
    response = client.post("/ask", json={"question": "What is Week 5 about?"})
    assert response.status_code == 200
    assert response.json()["answer"] != ""


def test_empty_question():
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 422


def test_question_too_long():
    response = client.post("/ask", json={"question": "a" * 501})
    assert response.status_code == 422


def test_unanswerable_question():
    response = client.post("/ask", json={"question": "What is the capital of Australia?"})
    assert response.status_code == 200
    answer = response.json()["answer"].lower().replace("’", "'")
    assert "don't know" in answer


def test_unknown_document():
    response = client.post("/ask", json={"question": "What is this about?", "document_id": "does-not-exist"})
    assert response.status_code == 404


def test_upload_and_ask():
    with open(SAMPLE, "rb") as f:
        response = client.post("/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    assert response.status_code == 200
    doc_id = response.json()["document_id"]

    response = client.post("/ask", json={"question": "What is this document about?", "document_id": doc_id})
    assert response.status_code == 200


def test_fake_pdf_refused():
    response = client.post("/upload", files={"file": ("fake.pdf", b"hello", "application/pdf")})
    assert response.status_code == 400


def test_blank_pdf_refused():
    response = client.post("/upload", files={"file": ("blank.pdf", make_blank_pdf(), "application/pdf")})
    assert response.status_code == 400
    assert "no readable text" in response.json()["detail"]