import json
import re
from typing import List, Dict, Any, Optional
import httpx
from backend.config import GEMINI_API_KEY, GEMINI_MODEL

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Helper to extract JSON object from markdown code blocks or raw text."""
    try:
        # Match json fenced block
        match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if match:
            return json.loads(match.group(1))
        # Match standalone outer braces
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return None

class AIService:
    def __init__(self):
        self.default_model = GEMINI_MODEL or "gemini-2.0-flash"

    async def call_gemini(self, prompt: str, system_prompt: str = "", api_key: Optional[str] = None) -> str:
        """Call Gemini REST API directly using free tier key."""
        key = api_key or GEMINI_API_KEY
        if not key:
            raise ValueError("NO_API_KEY")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.default_model}:generateContent?key={key}"
        
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"HƯỚNG DẪN HỆ THỐNG:\n{system_prompt}\n\n---\nYÊU CẦU:"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Đã hiểu hướng dẫn. Tôi sẽ thực hiện chính xác theo yêu cầu."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "topP": 0.9,
                "maxOutputTokens": 4096
            }
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise Exception(f"Gemini API Error {resp.status_code}: {resp.text}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            raise Exception("No content returned from Gemini API")

    async def analyze_syllabus(self, text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Analyze university syllabus, extract subject name, key concepts, difficulty."""
        # Trim text to avoid overflowing free tier tokens
        sample_text = text[:15000]

        prompt = f"""
Bạn là chuyên gia cố vấn học tập đại học. Hãy phân tích đề cương môn học/tài liệu ôn thi dưới đây và bóc tách thành các chủ đề trọng tâm để lập kế hoạch ôn thi.

NỘI DUNG TÀI LIỆU:
\"\"\"
{sample_text}
\"\"\"

YÊU CẦU TRẢ VỀ DUY NHẤT 1 ĐỐI TƯỢNG JSON có cấu trúc sau (không thêm bất kỳ văn bản ngoài JSON):
{{
  "subject_name": "Tên môn học (Ví dụ: Kinh tế vi mô, Triết học Mác-Lênin, Cấu trúc dữ liệu...)",
  "summary": "Tóm tắt ngắn gọn 2-3 câu về trọng tâm môn học và cấu trúc đề thi",
  "topics": [
    {{
      "code": "CH1",
      "title": "Tên chương / Chủ đề 1",
      "description": "Kiến thức cốt lõi sinh viên cần nắm trong chủ đề này",
      "difficulty": "Dễ" | "Trung bình" | "Khó",
      "estimated_hours": 2.5,
      "importance_score": 8.5
    }}
  ]
}}
Lưu ý:
- Phân loại độ khó khách quan dựa trên độ trừu tượng và tính toán.
- estimated_hours là số giờ học cần thiết để hiểu chủ đề này (từ 1.5 đến 4.0 giờ).
- importance_score từ 5.0 đến 10.0 (chủ đề thi thường gặp thì điểm cao).
"""
        # Try Gemini API if key is available
        key = api_key or GEMINI_API_KEY
        if key:
            try:
                raw_response = await self.call_gemini(
                    prompt=prompt,
                    system_prompt="Bạn là chuyên gia phân tích đề cương đại học, chỉ trả về JSON hợp lệ chuẩn xác 100%.",
                    api_key=key
                )
                parsed = extract_json_from_text(raw_response)
                if parsed and "topics" in parsed and len(parsed["topics"]) > 0:
                    return parsed
            except Exception as e:
                print(f"[AI Service] Gemini call failed, falling back to smart local extractor: {e}")

        # Intelligent Fallback Extractor (Runs 100% locally with 0 cost / offline)
        return self._local_syllabus_analyzer(text)

    def _local_syllabus_analyzer(self, text: str) -> Dict[str, Any]:
        """Smart rule-based extractor for Vietnamese university syllabi."""
        # Detect subject name
        subject_name = "Học phần Đại học"
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        for line in lines[:25]:
            if re.search(r"(môn học|học phần|đề cương|giáo trình|bài giảng|ôn tập)\s*[:\-]?\s*(.+)", line, re.I):
                match = re.search(r"(?:môn học|học phần|đề cương|giáo trình|bài giảng|ôn tập)\s*[:\-]?\s*(.+)", line, re.I)
                if match and len(match.group(1).strip()) > 3:
                    subject_name = match.group(1).strip()
                    break
            elif any(subj in line.lower() for subj in ["triết học", "kinh tế", "toán", "giải tích", "đại số", "lập trình", "pháp luật", "vật lý", "tiếng anh", "cấu trúc dữ liệu"]):
                subject_name = line
                break

        # Extract chapters / sections
        # Match patterns like "Chương 1:", "Chương I:", "Bài 1:", "Phần 1:", "1. Tổng quan..."
        chapter_regex = re.compile(
            r"^(chương\s+[0-9ivx]+|bài\s+[0-9ivx]+|phần\s+[0-9ivx]+|mục\s+[0-9ivx]+|[0-9]+\.)\s*[:\-–]?\s*(.+)$",
            re.I
        )

        extracted_topics = []
        current_code_idx = 1

        for idx, line in enumerate(lines):
            match = chapter_regex.match(line)
            if match:
                prefix = match.group(1).strip()
                title = match.group(2).strip()
                if len(title) > 3 and not title.isdigit():
                    # Look ahead a few lines for description
                    desc_lines = []
                    for next_line in lines[idx+1:idx+4]:
                        if not chapter_regex.match(next_line) and len(next_line) > 5:
                            desc_lines.append(next_line)
                    desc = " ".join(desc_lines) if desc_lines else f"Kiến thức trọng tâm của {title}"
                    if len(desc) > 150:
                        desc = desc[:147] + "..."

                    # Determine difficulty heuristically
                    title_lower = title.lower()
                    if any(w in title_lower for w in ["nâng cao", "ứng dụng", "thuật toán", "tính toán", "phân tích", "định lý", "quy luật"]):
                        diff = "Khó"
                        est_h = 3.5
                        imp = 9.0
                    elif any(w in title_lower for w in ["tổng quan", "mở đầu", "khái niệm", "định nghĩa", "giới thiệu", "cơ bản"]):
                        diff = "Dễ"
                        est_h = 1.5
                        imp = 7.0
                    else:
                        diff = "Trung bình"
                        est_h = 2.5
                        imp = 8.0

                    extracted_topics.append({
                        "code": f"CH{current_code_idx}",
                        "title": f"{prefix.upper()}: {title}",
                        "description": desc,
                        "difficulty": diff,
                        "estimated_hours": est_h,
                        "importance_score": imp
                    })
                    current_code_idx += 1

        # If no explicit chapter headers matched, split into logical conceptual blocks
        if len(extracted_topics) < 3:
            chunks = [c.strip() for c in re.split(r"\n{2,}", text) if len(c.strip()) > 80]
            chunks = chunks[:6]
            for idx, ch in enumerate(chunks, 1):
                first_sentence = ch.split(".")[0].strip()
                title = first_sentence[:60] if len(first_sentence) > 10 else f"Chủ đề trọng tâm {idx}"
                extracted_topics.append({
                    "code": f"CH{idx}",
                    "title": title,
                    "description": ch[:140] + "...",
                    "difficulty": "Trung bình" if idx % 2 == 0 else ("Dễ" if idx == 1 else "Khó"),
                    "estimated_hours": 2.0,
                    "importance_score": 8.0
                })

        return {
            "subject_name": subject_name,
            "summary": f"Đề cương môn {subject_name} gồm {len(extracted_topics)} chủ đề cốt lõi, bao quát toàn bộ lý thuyết và bài tập trọng tâm cho kỳ thi.",
            "topics": extracted_topics
        }

    async def answer_question(
        self,
        question: str,
        context_chunks: List[str],
        history: List[Dict[str, str]] = None,
        api_key: Optional[str] = None
    ) -> str:
        """Answer student questions grounded in syllabus/document materials."""
        context = "\n\n---\n\n".join(context_chunks[:4])
        
        prompt = f"""
Bạn là Trợ lý Gia sư AI hỗ trợ sinh viên ôn thi đại học.
Hãy trả lời câu hỏi của sinh viên DỰA TRÊN TÀI LIỆU ĐỀ CƯƠNG ĐÃ ĐƯỢC TẢI LÊN sau đây.

TÀI LIỆU THAM KHẢO:
\"\"\"
{context}
\"\"\"

CÂU HỎI CỦA SINH VIÊN:
{question}

NGUYÊN TẮC BẮT BUỘC:
1. Bám sát 100% nội dung trong tài liệu tham khảo để tránh ảo giác.
2. Trình bày ngắn gọn, gạch đầu dòng rõ ràng, có mẹo ghi nhớ cho sinh viên đi thi.
3. Nếu tài liệu không đề cập đến thông tin này, hãy thành thật nêu rõ và giải thích ngắn gọn dựa trên kiến thức học thuật chuẩn.
"""
        key = api_key or GEMINI_API_KEY
        if key:
            try:
                return await self.call_gemini(
                    prompt=prompt,
                    system_prompt="Bạn là gia sư AI đại học nhiệt tình, súc tích và giải thích dễ hiểu cho sinh viên.",
                    api_key=key
                )
            except Exception as e:
                print(f"[AI Chat] Gemini API failed: {e}")

        # Local intelligent answer generator
        return self._local_answer(question, context_chunks)

    def _local_answer(self, question: str, chunks: List[str]) -> str:
        """Local response when no API key is set."""
        if not chunks:
            return (
                "🤖 **Trợ lý ExamPlan (Chế độ Cục bộ):**\n\n"
                f"Bạn đang hỏi: *\"{question}\"*\n\n"
                "Hiện tại tài liệu chưa có đủ đoạn trích khớp với câu hỏi này. "
                "Bạn có thể nhập API Key Gemini (miễn phí tại aistudio.google.com) ở mục Cài đặt để AI phân tích chuyên sâu hơn nhé!"
            )
        
        best_chunk = chunks[0]
        return (
            f"🤖 **Trợ lý ExamPlan (Trích xuất từ Tài liệu Ôn thi):**\n\n"
            f"Đối với câu hỏi: *\"{question}\"*, tài liệu của môn học nêu rõ:\n\n"
            f"> {best_chunk[:300]}...\n\n"
            f"💡 **Mẹo làm bài thi:** Nắm vững các từ khóa cốt lõi trong đoạn trên và liên hệ với các câu hỏi lý thuyết hoặc bài tập tương ứng trong đề thi!"
        )

ai_service = AIService()
