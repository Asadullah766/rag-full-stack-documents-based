import os
from io import BytesIO
from PyPDF2 import PdfReader
import docx
import re

def load_file_content(file_or_path, from_disk=False) -> str:
    if from_disk:
        ext = os.path.splitext(file_or_path)[-1].lower()
        with open(file_or_path, "rb") as f:
            contents = f.read()
    else:
        contents = file_or_path.file.read()
        ext = os.path.splitext(file_or_path.filename)[-1].lower()

    if ext == ".pdf":
        return _load_pdf(contents)
    elif ext == ".docx":
        return _load_docx(contents)
    elif ext == ".txt":
        return _load_txt(contents)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def _load_pdf(file_bytes: bytes) -> str:
    text = ""
    pdf = PdfReader(BytesIO(file_bytes))
    for page in pdf.pages:
        text += page.extract_text() or ""
    
    # -------------------------------
    # Cleanup broken words / extra spaces / URLs
    # -------------------------------
    text = re.sub(r'\s+', ' ', text)                       # multiple spaces → single space
    text = re.sub(r'([A-Za-z])\s([A-Za-z])', r'\1\2', text)  # merge split words
    text = text.replace(' - ', '')                         # remove hyphenated breaks
    text = re.sub(r'(https?://)\s*', r'\1', text)         # fix spaces after http/https
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)          # remove space before punctuation
    
    return text.strip()

def _load_docx(file_bytes: bytes) -> str:
    doc = docx.Document(BytesIO(file_bytes))
    text = "\n".join([p.text for p in doc.paragraphs])
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _load_txt(file_bytes: bytes) -> str:
    text = file_bytes.decode("utf-8")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
