import io
import re
from pathlib import Path
from typing import Tuple, List, Dict
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument

def clean_vietnamese_text(text: str) -> str:
    """Normalize whitespace and remove non-printable/junk characters."""
    if not text:
        return ""
    # Replace weird space characters
    text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple consecutive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple consecutive spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pypdf."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for idx, page in enumerate(reader.pages):
        page_content = page.extract_text() or ""
        if page_content.strip():
            pages_text.append(f"--- TRANG {idx + 1} ---\n{page_content.strip()}")
    full_text = "\n\n".join(pages_text)
    return clean_vietnamese_text(full_text)

def parse_docx(file_bytes: bytes) -> str:
    """Extract text and tables from DOCX."""
    doc = DocxDocument(io.BytesIO(file_bytes))
    lines = []
    for p in doc.paragraphs:
        if p.text.strip():
            lines.append(p.text.strip())
    
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                lines.append(" | ".join(row_cells))
                
    return clean_vietnamese_text("\n".join(lines))

def parse_txt(file_bytes: bytes) -> str:
    """Extract plain text with utf-8 or latin-1 fallback."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8-sig", errors="replace")
    return clean_vietnamese_text(text)

async def parse_url(url: str) -> Tuple[str, str]:
    """Scrape and extract main text content from a web URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    # Extract page title
    title = soup.title.string.strip() if soup.title and soup.title.string else "Tài liệu trực tuyến"

    # Remove script, style, nav, footer, ads
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
        tag.decompose()

    # Prioritize article, main, or content divs
    main_elem = soup.find("article") or soup.find("main") or soup.find(id=re.compile(r"content|main|article", re.I)) or soup.body
    if not main_elem:
        main_elem = soup

    text = main_elem.get_text(separator="\n")
    return title, clean_vietnamese_text(text)

def extract_document_content(filename: str, content: bytes) -> Tuple[str, str]:
    """Auto-detect file extension and extract text."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf", parse_pdf(content)
    elif ext in [".docx", ".doc"]:
        return "docx", parse_docx(content)
    elif ext in [".txt", ".md"]:
        return "txt", parse_txt(content)
    else:
        # Fallback to plain text decode
        return "txt", parse_txt(content)
