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

                    full_title = f"{prefix.upper()}: {title}".strip()
                    # Deduplicate topics with same normalized title
                    norm_title = re.sub(r"\s+", " ", full_title.lower())
                    if not any(re.sub(r"\s+", " ", t["title"].lower()) == norm_title for t in extracted_topics):
                        extracted_topics.append({
                            "code": f"CH{current_code_idx}",
                            "title": full_title,
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
                norm_title = re.sub(r"\s+", " ", title.lower())
                if not any(re.sub(r"\s+", " ", t["title"].lower()) == norm_title for t in extracted_topics):
                    extracted_topics.append({
                        "code": f"CH{current_code_idx}",
                        "title": title,
                        "description": ch[:140] + "...",
                        "difficulty": "Trung bình" if idx % 2 == 0 else ("Dễ" if idx == 1 else "Khó"),
                        "estimated_hours": 2.0,
                        "importance_score": 8.0
                    })
                    current_code_idx += 1

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

    async def generate_study_lesson(
        self,
        task_title: str,
        topic_title: str,
        context_chunks: List[str],
        target_goal: str = "advanced",
        summary_mode: str = "quick", # "quick" (3 phút ngắn gọn) | "detailed" (Đầy đủ chuyên sâu)
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate 3-5 core concepts, 1 quick 2-minute quiz, and optional advanced materials."""
        context = "\n\n---\n\n".join(context_chunks[:4]) if context_chunks else ""
        is_advanced = target_goal in ["advanced", "g gioi", "gioi", "xuat sac"]
        is_detailed = summary_mode == "detailed"

        mode_instruction = (
            "CHẾ ĐỘ TÓM TẮT: ĐẦY ĐỦ & CHUYÊN SÂU (Detailed Mode)\n"
            "- Giải thích cặn kẽ bản chất vật lý/toán học/chuyên môn, chứng minh công thức ngắn gọn, điều kiện biên và các trường hợp ngoại lệ.\n"
            "- Nêu rõ các dạng bài toán tự luận hoặc tính toán phức tạp hay gặp trong đề thi."
            if is_detailed else
            "CHẾ ĐỘ TÓM TẮT: CÔ ĐỌNG 3 PHÚT (Quick Mode)\n"
            "- Tập trung tối đa vào công thức chốt hạ, định nghĩa 1-2 câu súc tích nhất, điều kiện tiên quyết cần nhớ ngay trước giờ thi."
        )

        prompt = f"""
Bạn là chuyên gia giảng dạy đại học hàng đầu về môn học này. Hãy trích xuất và giảng giải KIẾN THỨC CHUYÊN MÔN CỤ THỂ, TRỰC DIỆN từ tài liệu đề cương cho bài học sau:

TÊN BÀI HỌC: {task_title}
CHỦ ĐỀ CHÍNH: {topic_title or task_title}
MỤC TIÊU: {'Nâng cao / Điểm giỏi (8.5 - 10.0)' if is_advanced else 'Cơ bản / Pass môn (5.0 - 7.0)'}
{mode_instruction}

NỘI DUNG TÀI LIỆU TRÍCH XUẤT TỪ ĐỀ CƯƠNG:
\"\"\"
{context if context else "Dựa vào kiến thức chuyên môn học thuật chính xác về chủ đề này."}
\"\"\"

NGUYÊN TẮC BẮT BUỘC VỀ NỘI DUNG (VI PHẠM LÀ THẤT BẠI):
1. TÓM TẮT KIẾN THỨC CHUYÊN MÔN THỰC TẾ:
   - Phải trích xuất ĐỊNH NGHĨA CHÍNH XÁC, ĐỊNH LUẬT, CÔNG THỨC TOÁN/LÝ/HÓA/TIN HỌC, ĐIỀU KIỆN ÁP DỤNG, BẢN CHẤT HIỆN TƯỢNG, HỆ QUẢ.
   - TUYỆT ĐỐI KHÔNG viết các câu khuyên mẹo học, kỹ năng mềm hay meta-learning sáo rỗng như "hãy đọc kỹ", "lập thời gian biểu", "vẽ sơ đồ tư duy", "ôn tập đều đặn".
   - Mỗi mục phải có tên rõ ràng và phần nội dung chuyên môn cô đọng, có công thức/ký hiệu nếu môn tự nhiên.
2. QUICK-QUIZ TRẮC NGHIỆM:
   - Câu hỏi trắc nghiệm PHẢI HỎI VỀ KIẾN THỨC CHUYÊN MÔN CỤ THỂ, CÔNG THỨC HOẶC TÍNH TOÁN CỦA CHỦ ĐỀ NÀY (Ví dụ: "Công thức tính từ thông phi là?", "Theo định luật Lenz, dòng điện cảm ứng có chiều thế nào?", "Điều kiện để xảy ra hiện tượng... là?").
   - TUYỆT ĐỐI KHÔNG hỏi các câu kiểu: "Yếu tố nào quan trọng nhất khi học...", "Làm thế nào để nhớ bài...", "Phương pháp nào sau đây giúp thi tốt...".
   - 4 phương án A, B, C, D rõ ràng với 1 đáp án đúng duy nhất.

YÊU CẦU ĐẦU RA (CHỈ TRẢ VỀ JSON HỢP LỆ, KHÔNG KÈM VĂN BẢN NGOÀI):
{{
  "task_title": "{task_title}",
  "summary_mode": "{summary_mode}",
  "core_concepts": [
    {{
      "title": "Tên khái niệm / Định luật / Công thức cụ thể",
      "summary": "Nội dung học thuật chi tiết: Định nghĩa, công thức toán học/khoa học, hiện tượng hoặc quy tắc chuyên môn.",
      "tip": "Đặc điểm nhận dạng trong bài tập hoặc hệ quả công thức quan trọng"
    }}
  ],
  "quick_quiz": {{
    "question": "Câu hỏi chuyên môn / công thức / khái niệm cụ thể của bài học?",
    "options": [
      "A. Nội dung lựa chọn A",
      "B. Nội dung lựa chọn B",
      "C. Nội dung lựa chọn C",
      "D. Nội dung lựa chọn D"
    ],
    "correct_index": 0,
    "explanation": "Giải thích chi tiết về mặt chuyên môn/công thức tại sao đáp án này đúng."
  }},
  "advanced_materials": [
    {{
      "title": "Dạng bài toán / Chuyên đề vận dụng cao",
      "type": "Vận dụng cao (Điểm 9 - 10)",
      "description": "Các bài toán biến thiên, phương pháp giải nhanh hoặc trường hợp phức tạp"
    }}
  ]
}}

LƯU Ý: "core_concepts" phải có từ 3 đến 5 mục kiến thức học thuật chuyên sâu.
"""
        key = api_key or GEMINI_API_KEY
        if key:
            try:
                raw_text = await self.call_gemini(
                    prompt=prompt,
                    system_prompt="Bạn là giáo sư đại học giảng dạy môn học này. Bạn chỉ trả lời kiến thức chuyên môn thực tế, công thức, định lý và bài tập trắc nghiệm học thuật, không nói chuyện ngoài lề.",
                    api_key=key
                )
                parsed = extract_json_from_text(raw_text)
                if parsed and "core_concepts" in parsed and "quick_quiz" in parsed:
                    return parsed
            except Exception as e:
                print(f"[Study Lesson] Gemini API failed: {e}")

        # Local fallback lesson generator grounded in context
        return self._local_study_lesson(task_title, topic_title, context_chunks, is_advanced)

    def _local_study_lesson(
        self,
        task_title: str,
        topic_title: str,
        context_chunks: List[str],
        is_advanced: bool
    ) -> Dict[str, Any]:
        """Generate concrete domain-specific micro-lesson offline extracting real textbook lines."""
        topic_name = topic_title or task_title
        combined_text = "\n".join(context_chunks) if context_chunks else ""
        
        # Extract substantial academic sentences/paragraphs from raw syllabus
        raw_lines = [
            line.strip().lstrip("-*•0123456789. ") 
            for line in combined_text.split("\n") 
            if len(line.strip()) > 20 and not line.strip().startswith("#")
        ]

        def get_clean_line(idx: int, default: str) -> str:
            if idx < len(raw_lines):
                return raw_lines[idx][:250]
            return default

        concept1_content = get_clean_line(
            0,
            f"Định nghĩa và bản chất của {topic_name}: Xác định rõ các thông số đặc trưng, tiên đề cơ bản và phạm vi nghiên cứu của chủ đề."
        )
        concept2_content = get_clean_line(
            1,
            f"Nguyên lý vận hành & Công thức liên hệ: Mối quan hệ giữa các biến số, phương trình toán học và quy luật chi phối {task_title}."
        )
        concept3_content = get_clean_line(
            2,
            f"Tính chất đặc trưng & Các trường hợp giới hạn: Sự biến thiên của hệ thống khi các điều kiện biên hoặc tham số thay đổi."
        )
        concept4_content = get_clean_line(
            3,
            f"Hệ quả thực nghiệm và ứng dụng tính toán: Phương pháp áp dụng quy tắc giải các bài toán định lượng và giải thích hiện tượng quan sát."
        )

        core_concepts = [
            {
                "title": f"Định nghĩa & Bản chất cốt lõi: {topic_name[:40]}",
                "summary": concept1_content,
                "tip": f"Từ khóa chuyên ngành cốt lõi cần nhớ: {topic_name.split()[-1] if topic_name else 'Thuật ngữ'}."
            },
            {
                "title": f"Quy luật & Công thức liên hệ của {task_title[:35]}",
                "summary": concept2_content,
                "tip": "Chú ý đơn vị đo lường và dấu âm/dương trong các phương trình liên hệ."
            },
            {
                "title": "Tính chất đặc trưng & Điều kiện áp dụng",
                "summary": concept3_content,
                "tip": "Đặc biệt chú ý điều kiện tiên quyết để định lý/quy tắc có hiệu lực."
            },
            {
                "title": "Hệ quả & Dạng bài tập điển hình",
                "summary": concept4_content,
                "tip": "Nhận diện dạng bài thông qua các đại lượng đã cho và đại lượng cần tìm."
            }
        ]

        # Domain-specific quiz question based on actual topic name
        quick_quiz = {
            "question": f"Về mặt chuyên môn của nội dung '{topic_name}', phát biểu hoặc tính chất nào sau đây là ĐÚNG?",
            "options": [
                f"A. {concept1_content[:90]}...",
                f"B. Đại lượng trong {topic_name[:25]} luôn triệt tiêu về 0 ở mọi điều kiện bất kỳ",
                f"C. Hoàn toàn độc lập và không tuân theo các định luật bảo toàn của hệ",
                f"D. Chỉ xuất hiện trong môi trường lý tưởng và không có ý nghĩa thực nghiệm"
            ],
            "correct_index": 0,
            "explanation": f"Khái niệm chuẩn xác: {concept1_content[:150]}... Đây là nền tảng chi phối bản chất của {topic_name}."
        }

        advanced_materials = []
        if is_advanced:
            advanced_materials = [
                {
                    "title": f"Dạng bài phân loại điểm 9-10: Bài toán phi tuyến & đa biến trong {topic_name}",
                    "type": "Vận dụng cao",
                    "description": f"Phân tích hệ phương trình khi các hệ số phụ thuộc vào thời gian/trạng thái. Thiết lập mô hình giải tích chính xác."
                },
                {
                    "title": f"Chuyên đề nâng cao: Các định luật mở rộng và trường hợp đặc biệt",
                    "type": "Chuyên sâu",
                    "description": f"Kỹ thuật biến đổi đưa các bài toán phức tạp của {task_title} về dạng chuẩn tắc để tính toán nhanh trong phòng thi."
                }
            ]

        return {
            "task_title": task_title,
            "core_concepts": core_concepts,
            "quick_quiz": quick_quiz,
            "advanced_materials": advanced_materials
        }

ai_service = AIService()

