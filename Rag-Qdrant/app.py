import os
import time
import streamlit as st
import requests
from fastapi import UploadFile

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="RAG-Qdrant Chatbot", layout="wide")
st.title("🤖 RAG-Qdrant Chatbot")
st.markdown("Upload PDFs or DOCX, ingest them, and query your documents!")

# ----------------- Sidebar: File Upload -----------------
st.sidebar.header("📂 Upload Documents")
uploaded_files = st.sidebar.file_uploader(
    "Select your PDF or DOCX files", type=["pdf", "docx"], accept_multiple_files=True
)
process_btn = st.sidebar.button("🚀 Process Files")

# ----------------- Helper Functions -----------------
def upload_file_to_backend(file: UploadFile):
    files = {"file": (file.name, file.getvalue())}
    try:
        response = requests.post(f"{API_URL}/ingest", files=files, timeout=60)
        return response.json()
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        return None

def check_status(filename: str):
    try:
        response = requests.get(f"{API_URL}/status/{filename}", timeout=10)
        return response.json()
    except Exception as e:
        return {"status": f"failed: {e}"}

# ✅ Extract only answer string from backend JSON
def ask_question(query: str):
    try:
        response = requests.post(f"{API_URL}/ask", json={"query": query}, timeout=30)
        data = response.json()
        return data.get("answer", "⚠️ No answer returned.")  # only answer string
    except Exception as e:
        return f"Error: {e}"

# ----------------- File Ingestion -----------------
if process_btn:
    if not uploaded_files:
        st.warning("⚠️ Please upload at least one file.")
    else:
        for f in uploaded_files:
            st.info(f"📤 Uploading **{f.name}** ...")
            result = upload_file_to_backend(f)
            if result:
                st.success(result.get("message"))
                filename = f.name
                with st.spinner(f"⏳ Ingesting {filename} ..."):
                    status = "processing"
                    while status == "processing":
                        time.sleep(2)
                        status_resp = check_status(filename)
                        status = status_resp.get("status", "")
                    if "completed" in status:
                        st.success(f"✅ {filename} ingestion completed!")
                    else:
                        st.error(f"❌ {filename} ingestion failed: {status}")

# ----------------- Chat History -----------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

chat_container = st.container()

# ----------------- User Input -----------------
user_query = st.chat_input("💬 Ask a question about your documents...")
if user_query:
    with st.spinner("🤖 Thinking..."):
        answer_text = ask_question(user_query)

    # Save messages
    st.session_state.chat_history.append(("user", user_query))
    st.session_state.chat_history.append(("ai", answer_text))

# ----------------- Display Chat -----------------
with chat_container:
    for sender, msg in st.session_state.chat_history:
        if sender == "user":
            st.chat_message("user").write(msg)
        else:
            # Display Markdown properly (headings, subheadings, bullets)
            st.chat_message("assistant").markdown(
                f"""
<div style="
    background-color:#f8f9fa; 
    padding:15px; 
    border-radius:10px; 
    border:1px solid #ddd; 
    color:#000;         /* consistent black text */
    font-size:16px; 
    line-height:1.6;
">
{msg}
</div>
""",
                unsafe_allow_html=True
            )
