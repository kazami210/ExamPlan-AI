import io
import re
import secrets
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument
import pymupdf
from backend.config import UPLOAD_DIR

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

def extract_pdf_with_slides(file_bytes: bytes, doc_prefix: str = "doc") -> Tuple[str, List[str], int]:
    """
    Renders every PDF slide/page into high-resolution PNG images for authentic viewing,
    and extracts structured text per page.
    Returns: (full_extracted_text, list_of_slide_image_urls, total_pages)
    """
    slides_dir = UPLOAD_DIR / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    pages_text = []
    slide_urls = []

    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_text = page.get_text() or ""
        if page_text.strip():
            pages_text.append(f"--- TRANG {page_num} ---\n{page_text.strip()}")

        # Render page to slide image (DPI 150 gives crisp readability and fast web loading)
        try:
            pix = page.get_pixmap(dpi=150)
            img_filename = f"{doc_prefix}_p{page_num}_{secrets.token_hex(4)}.png"
            img_path = slides_dir / img_filename
            pix.save(str(img_path))
            slide_urls.append(f"/static/slides/{img_filename}")
        except Exception as e:
            # Fallback to checking embedded images if page rendering fails
            try:
                embedded_imgs = page.get_images()
                for img_info in embedded_imgs[:2]:
                    xref = img_info[0]
                    base_img = doc.extract_image(xref)
                    img_ext = base_img.get("ext", "png")
                    img_filename = f"{doc_prefix}_p{page_num}_img_{xref}_{secrets.token_hex(3)}.{img_ext}"
                    img_path = slides_dir / img_filename
                    with open(img_path, "wb") as f:
                        f.write(base_img["image"])
                    slide_urls.append(f"/static/slides/{img_filename}")
            except Exception:
                pass

    doc.close()
    full_text = clean_vietnamese_text("\n\n".join(pages_text))
    return full_text, slide_urls, total_pages

def extract_pptx_with_slides(file_bytes: bytes, doc_prefix: str = "doc") -> Tuple[str, List[str], int]:
    """
    Extracts text and embedded images/diagrams from Microsoft PowerPoint (.pptx) presentations.
    """
    import pptx
    slides_dir = UPLOAD_DIR / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    prs = pptx.Presentation(io.BytesIO(file_bytes))
    total_slides = len(prs.slides)
    slides_text = []
    slide_urls = []

    for idx, slide in enumerate(prs.slides, 1):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
            if shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
                try:
                    img_ext = shape.image.ext or "png"
                    img_name = f"{doc_prefix}_slide_{idx}_{secrets.token_hex(4)}.{img_ext}"
                    img_path = slides_dir / img_name
                    with open(img_path, "wb") as f:
                        f.write(shape.image.blob)
                    slide_urls.append(f"/static/slides/{img_name}")
                except Exception:
                    pass
        if texts:
            slides_text.append(f"--- SLIDE {idx} ---\n" + "\n".join(texts))

    full_text = clean_vietnamese_text("\n\n".join(slides_text))
    return full_text, slide_urls, total_slides

def extract_docx_with_images(file_bytes: bytes, doc_prefix: str = "doc") -> Tuple[str, List[str], int]:
    """
    Extracts text, tables, and embedded figures/images from Word documents (.docx).
    """
    slides_dir = UPLOAD_DIR / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

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

    # Extract embedded diagrams and illustrations
    image_urls = []
    img_idx = 1
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            try:
                img_part = rel.target_part
                content_type = img_part.content_type.lower()
                ext = "png"
                if "jpeg" in content_type or "jpg" in content_type:
                    ext = "jpg"
                elif "gif" in content_type:
                    ext = "gif"
                elif "svg" in content_type:
                    ext = "svg"
                
                # Only keep substantial figures (filter out tiny icons < 1KB)
                if len(img_part.blob) > 1500:
                    img_name = f"{doc_prefix}_fig_{img_idx}_{secrets.token_hex(4)}.{ext}"
                    img_path = slides_dir / img_name
                    with open(img_path, "wb") as f:
                        f.write(img_part.blob)
                    image_urls.append(f"/static/slides/{img_name}")
                    img_idx += 1
            except Exception:
                pass

    return clean_vietnamese_text("\n".join(lines)), image_urls, 1

def parse_docx(file_bytes: bytes) -> str:
    """Extract text from docx for backwards compatibility."""
    text, _, _ = extract_docx_with_images(file_bytes)
    return text

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
    title = soup.title.string.strip() if soup.title and soup.title.string else "Tài liệu trực tuyến"

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
        tag.decompose()

    main_elem = soup.find("article") or soup.find("main") or soup.find(id=re.compile(r"content|main|article", re.I)) or soup.body
    if not main_elem:
        main_elem = soup

    text = main_elem.get_text(separator="\n")
    return title, clean_vietnamese_text(text)

def extract_document_content(filename: str, content: bytes, doc_prefix: str = "doc") -> Tuple[str, str, List[str], int]:
    """
    Auto-detect file extension and extract text, embedded images, and rendered slide pages directly.
    Returns: (file_type, extracted_text, list_of_slide_images, total_pages)
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        text, slide_imgs, total_pages = extract_pdf_with_slides(content, doc_prefix=doc_prefix)
        return "pdf", text, slide_imgs, total_pages
    elif ext in [".pptx", ".ppt"]:
        text, slide_imgs, total_pages = extract_pptx_with_slides(content, doc_prefix=doc_prefix)
        return "pptx", text, slide_imgs, total_pages
    elif ext in [".docx", ".doc"]:
        text, slide_imgs, total_pages = extract_docx_with_images(content, doc_prefix=doc_prefix)
        return "docx", text, slide_imgs, total_pages
    elif ext in [".txt", ".md"]:
        return "txt", parse_txt(content), [], 1
    else:
        return "txt", parse_txt(content), [], 1
