import uuid
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

load_dotenv()

class PDFError(Exception):
    pass

embedding = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")

Max_chunk=95
def build_retriever(pdf_path):
    try:
        docs = PyPDFLoader(pdf_path).load()
    except Exception as e:
        print(e)
        raise PDFError("This file could not be read as a PDF.")

    text = "".join(d.page_content for d in docs).strip()
    if len(text) < 50 * len(docs):
        raise PDFError("This PDF has no readable text. Scanned PDFs are not supported.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
    chunks = splitter.split_documents(docs)

    if len(chunks) > Max_chunk:
        raise PDFError("This PDF is too long. The limit is " + str(Max_chunk) + " chunks.")


    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        collection_name="doc_" + uuid.uuid4().hex[:8]
    )
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    bm25 = BM25Retriever.from_documents(chunks)
    bm25.k = 5

    retriever = EnsembleRetriever(retrievers=[bm25, vector_retriever], weights=[0.4, 0.6])
    return retriever, len(docs), len(chunks)


def ask_pdf(query, retriever):
    best_docs = retriever.invoke(query)[:5]

    context = ""
    for doc in best_docs:
        context = context + "[Page " + str(doc.metadata.get("page", "?")) + "]: " + doc.page_content + "\n\n"

    prompt = f"""Answer the question using only the context below.
If the context contains information that answers the question, give that answer, even if the wording of the question is slightly different from the text.
Say "I don't know" only if the context has no relevant information at all.

Context:
{context}

Question: {query}

Answer:"""

    response = llm.invoke(prompt)
    if isinstance(response.content, list):
        answer = response.content[0]["text"]
    else:
        answer = response.content
    return answer


if __name__ == "__main__":
    r = build_retriever("Road map.pdf")
    print(ask_pdf("What is the skills are ?", r))