# PDF RAG API

A FastAPI service that answers questions about a PDF using hybrid search
(BM25 + vector search) and Gemini. You can upload your own PDF.

## How it works
1. A PDF is split into chunks and embedded.
2. A question runs through BM25 and vector search, and the best chunks go to Gemini.
3. Gemini answers only from those chunks, or says "I don't know".

## Run it
pip install -r requirements.txt
Create a .env file with: GOOGLE_API_KEY=your_key
uvicorn main:app
Then open http://127.0.0.1:8000/docs

## Endpoints
- GET /health
- POST /upload (send a PDF, get a document_id)
- POST /ask  {"question": "...", "document_id": "optional"}

## Limits
- PDFs with readable text only (scanned PDFs are refused)
- Maximum 5 MB and about 90 chunks
- 5 uploaded documents are kept in memory; they disappear on restart