from flask import Flask, render_template, request, jsonify
import os
from io import BytesIO
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from langchain_core.prompts import PromptTemplate
from langchain_chroma import Chroma

app = Flask(__name__)

PROMPT_TEMPLATE = """
Answer the question using ONLY the context below.

Context:
{context}

Question:
{question}

Answer:
"""


prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)


def read_uploaded_document(file_storage):
    if file_storage is None or file_storage.filename == "":
        return ""

    file_bytes = file_storage.read()
    filename = file_storage.filename.lower()

    if filename.endswith(".docx"):
        document = Document(BytesIO(file_bytes))
        return "\n".join(para.text for para in document.paragraphs if para.text)

    if filename.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")

    raise ValueError("Unsupported file type. Please upload a .docx or .txt file.")


def build_document_text(uploaded_text, pasted_text):
    parts = []
    if uploaded_text:
        parts.append(uploaded_text)
    if pasted_text:
        parts.append(pasted_text)

    document_text = "\n\n".join(parts).strip()
    if not document_text:
        raise ValueError("Please upload a document or paste text for the model to read.")

    return document_text


def create_vector_store(document_text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(document_text)
    if not chunks:
        raise ValueError("The provided document is too short to create embeddings.")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    return Chroma.from_texts(texts=chunks, embedding=embeddings)


def get_relevant_context(vector_db, question):
    retriever = vector_db.as_retriever(search_kwargs={"k": 2})

    try:
        docs = retriever.invoke(question)
    except AttributeError:
        docs = retriever.get_relevant_documents(question)
    except Exception:
        docs = retriever.get_relevant_documents(question)

    if not docs:
        raise ValueError("Could not retrieve relevant text from the document.")

    return "\n\n".join(getattr(doc, "page_content", str(doc)) for doc in docs)


def ask_question(question, context):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    final_prompt = prompt.format(context=context, question=question)

    for attempt in range(2):
        try:
            response = llm.invoke(final_prompt)
            return getattr(response, "content", str(response))
        except ChatGoogleGenerativeAIError as exc:
            if "RESOURCE_EXHAUSTED" in str(exc) and attempt == 0:
                import time
                time.sleep(30)
                continue
            raise

    raise ValueError("The language model failed to return an answer.")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    try:
        api_key = request.form.get("api_key", "").strip()
        question = request.form.get("question", "").strip()
        pasted_text = request.form.get("document_text", "").strip()
        uploaded_text = read_uploaded_document(request.files.get("document_file"))

        if not api_key:
            raise ValueError("Please enter your Google API key.")
        if not question:
            raise ValueError("Please enter your question.")

        os.environ["GOOGLE_API_KEY"] = api_key
        document_text = build_document_text(uploaded_text, pasted_text)
        vector_db = create_vector_store(document_text)
        context = get_relevant_context(vector_db, question)
        answer = ask_question(question, context)

        result = {"success": True, "answer": answer, "context": context}
        if is_ajax:
            return jsonify(result)
        return render_template("index.html", result=result)

    except Exception as exc:
        result = {"success": False, "error": str(exc)}
        if is_ajax:
            return jsonify(result), 400
        return render_template("index.html", result=result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
