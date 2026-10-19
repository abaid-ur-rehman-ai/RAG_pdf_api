import os
import tempfile
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from rag import build_retriever, ask_pdf ,PDFError

MAX_SIZE = 5 * 1024 * 1024
MAX_DOCS = 5

documents = {"default": build_retriever("Road map.pdf")[0]}


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    document_id: str = "default"


class AskResponse(BaseModel):
    answer: str
    document_id: str

class UploadResponse(BaseModel):
    document_id: str
    pages: int
    chunks: int


app = FastAPI(title="PDF RAG API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    retriever = documents.get(body.document_id)
    if retriever is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        answer = ask_pdf(body.question, retriever)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=503, detail="The AI service is busy. Please try again in a minute.")
    return {"answer": answer, "document_id": body.document_id}

@app.post("/upload", response_model=UploadResponse)
def upload(file: UploadFile = File(...)):
    data = file.file.read()

    if not (file.filename or "").lower().endswith(".pdf") or not data.startswith(b"%PDF"):
        print("Refused: name =", file.filename, "| first bytes =", data[:8])   # NEW
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="The file is too large. The limit is 5 MB.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name

    try:
        retriever, pages, chunks = build_retriever(path)
    except PDFError as e:
        print("Refused:", e)                                                    # NEW
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=503, detail="The AI service is busy. Please try again in a minute.")
    finally:
        os.remove(path)

    doc_id = uuid.uuid4().hex
    documents[doc_id] = retriever

    uploaded = [k for k in documents if k != "default"]
    if len(uploaded) > MAX_DOCS:
        del documents[uploaded[0]]

    return {"document_id": doc_id, "pages": pages, "chunks": chunks}