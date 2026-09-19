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
        """Generate structured lesson: Core Concepts & Formulas merged, Examples separated, Quick Quiz."""
        context = "\n\n---\n\n".join(context_chunks[:4]) if context_chunks else ""
        is_advanced = target_goal in ["advanced", "g gioi", "gioi", "xuat sac"]
        is_detailed = summary_mode == "detailed"

        mode_instruction = (
            "CHẾ ĐỘ TÓM TẮT: ĐẦY ĐỦ & CHUYÊN SÂU (Detailed Mode)\n"
            "- Phần Khái niệm & Công thức: Giải thích cặn kẽ bản chất học thuật, ý nghĩa từng đại lượng, đơn vị, điều kiện biên, các trường hợp ngoại lệ.\n"
            "- Phần Ví dụ & Bài tập minh họa: Đưa ra 1 - 2 ví dụ cụ thể có các bước giải chi tiết từng bước (Step-by-step) để người học làm theo được ngay.\n"
            "- Tài liệu nâng cao: Phân tích các bẫy đề thi và dạng bài phân loại điểm 9-10."
            if is_detailed else
            "CHẾ ĐỘ TÓM TẮT: CÔ ĐỌNG 3 PHÚT (Quick Mode)\n"
            "- Phần Khái niệm & Công thức: Cực kỳ súc tích. Gộp thẳng định nghĩa và công thức chốt hạ vào 1-2 câu ngắn gọn, dễ nhớ nhất.\n"
            "- Phần Ví dụ & Bài tập: Chỉ đưa ra dạng bài toán/tình huống nhận diện nhanh trong 30 giây, không lan man.\n"
            "- Mẹo thi: Chỉ ra từ khóa then chốt cần ghi nhớ ngay khi gặp câu hỏi trong đề thi."
        )

        prompt = f"""
Bạn là giảng viên đại học xuất sắc. Hãy phân tích tài liệu đề cương và biên soạn bài học theo cấu trúc chuẩn sư phạm:

TÊN BÀI HỌC: {task_title}
CHỦ ĐỀ CHÍNH: {topic_title or task_title}
MỤC TIÊU: {'Nâng cao / Điểm giỏi (8.5 - 10.0)' if is_advanced else 'Cơ bản / Pass môn (5.0 - 7.0)'}
{mode_instruction}

NỘI DUNG TÀI LIỆU TRÍCH XUẤT TỪ ĐỀ CƯƠNG:
\"\"\"
{context if context else "Dựa vào kiến thức chuyên môn học thuật chính xác về chủ đề này."}
\"\"\"

NGUYÊN TẮC BẮT BUỘC VỀ BỐ CỤC:
1. GỘP CHUNG KHÁI NIỆM & CÔNG THỨC: Định nghĩa và công thức toán/lý/hóa liên quan phải nằm chung trong cùng 1 khối để người học liên kết ngay bản chất với công thức tính toán.
2. TÁCH RIÊNG PHẦN VÍ DỤ / BÀI TẬP: Tuyệt đối không để lẫn nội dung ví dụ vào phần định nghĩa. Các câu như "Ví dụ 1: Khung dây...", "Bài toán mẫu:" phải đưa riêng vào mục "examples".
3. TRÁNH CÂU META-LEARNING CHUNG CHUNG: Không viết mẹo học sáo rỗng như "chăm chỉ", "lập kế hoạch". Phải là công thức, đại lượng, hiện tượng vật lý/chuyên môn thật.

YÊU CẦU ĐẦU RA (CHỈ TRẢ VỀ JSON HỢP LỆ, KHÔNG KÈM VĂN BẢN NGOÀI):
{{
  "task_title": "{task_title}",
  "summary_mode": "{summary_mode}",
  "core_concepts": [
    {{
      "title": "Tên định nghĩa & công thức (Ví dụ: Định luật Lenz & Chiều dòng điện cảm ứng)",
      "definition": "Định nghĩa bản chất lý thuyết ngắn gọn, chuẩn xác",
      "formula": "Công thức toán học/khoa học liên quan (hoặc biểu thức quy tắc, ví dụ: e_c = - dPhi / dt)",
      "unit_and_note": "Ý nghĩa các đại lượng, đơn vị đo hoặc điều kiện áp dụng",
      "tip": "Mẹo thi thực chiến hoặc bẫy cần tránh"
    }}
  ],
  "examples": [
    {{
      "title": "Ví dụ minh họa / Dạng bài tập cụ thể",
      "problem": "Đề bài ví dụ cụ thể (số liệu hoặc tình huống đề cương đưa ra)",
      "solution": "Phương pháp giải / Hướng dẫn xử lý chi tiết"
    }}
  ],
  "quick_quiz": {{
    "question": "Câu hỏi trắc nghiệm chuyên môn cụ thể của bài học?",
    "options": [
      "A. Lựa chọn A",
      "B. Lựa chọn B",
      "C. Lựa chọn C",
      "D. Lựa chọn D"
    ],
    "correct_index": 0,
    "explanation": "Giải thích chi tiết tại sao đúng dựa trên công thức và định nghĩa."
  }},
  "advanced_materials": [
    {{
      "title": "Chuyên đề vận dụng cao / Mở rộng",
      "type": "Vận dụng cao",
      "description": "Nội dung nâng cao hướng tới điểm 9-10"
    }}
  ]
}}
"""
        key = api_key or GEMINI_API_KEY
        if key:
            try:
                raw_text = await self.call_gemini(
                    prompt=prompt,
                    system_prompt="Bạn là giáo sư đại học. Bạn giải thích kiến thức chuyên môn, công thức và ví dụ cụ thể, bố cục rõ ràng chuẩn mực theo JSON.",
                    api_key=key
                )
                parsed = extract_json_from_text(raw_text)
                if parsed and "core_concepts" in parsed and "quick_quiz" in parsed:
                    return parsed
            except Exception as e:
                print(f"[Study Lesson] Gemini API failed: {e}")

        # Local fallback lesson generator grounded in context
        return self._local_study_lesson(task_title, topic_title, context_chunks, is_advanced, summary_mode)

    def _local_study_lesson(
        self,
        task_title: str,
        topic_title: str,
        context_chunks: List[str],
        is_advanced: bool,
        summary_mode: str = "quick"
    ) -> Dict[str, Any]:
        """Generate concrete domain-specific micro-lesson offline extracting real textbook lines."""
        topic_name = topic_title or task_title
        combined_text = "\n".join(context_chunks) if context_chunks else ""
        is_detailed = summary_mode == "detailed"

        # Separate regular lines vs example lines ("Ví dụ", "Bài tập", "VD")
        raw_lines = [
            line.strip().lstrip("-*•0123456789. ") 
            for line in combined_text.split("\n") 
            if len(line.strip()) > 15 and not line.strip().startswith("#")
        ]

        concept_lines = []
        example_lines = []

        for line in raw_lines:
            low = line.lower()
            if any(k in low for k in ["ví dụ", "vi du", "bài tập", "bai tap", "vd:", "vd 1", "vd 2", "bài toán"]):
                example_lines.append(line)
            else:
                concept_lines.append(line)

        def get_line(source_list: list, idx: int, default: str) -> str:
            if idx < len(source_list):
                return source_list[idx]
            return default

        # Clean topic title for formula association
        short_topic = re.sub(r"\(và\s*\d+\s*tiểu mục liên quan\)", "", topic_name, flags=re.I).strip()
        short_topic = re.sub(r"^chương\s*\d+:\s*", "", short_topic, flags=re.I).strip()
        if not short_topic or len(short_topic) < 3:
            short_topic = "Cảm ứng điện từ"

        if is_detailed:
            # Detailed mode: Deep explanation, derivations, complete steps
            c1_def = get_line(concept_lines, 0, f"Định luật và hiện tượng cơ bản của {short_topic}: Xác định sự biến thiên từ thông sinh ra suất điện động cảm ứng.")
            c1_formula = "e_c = - ΔΦ / Δt  hoặc  e_c = - dΦ / dt" if ("suất điện động" in short_topic.lower() or "cảm ứng" in short_topic.lower()) else "Φ = B · S · cos(α)"
            
            c2_def = get_line(concept_lines, 1, "Chiều dòng điện cảm ứng tuân theo Định luật Lenz: Dòng điện cảm ứng có chiều sao cho từ trường do nó sinh ra có tác dụng chống lại sự biến thiên của từ thông ban đầu.")
            c2_formula = "i_c = e_c / R = - (1/R) · (dΦ / dt)"

            c3_def = get_line(concept_lines, 2, "Hiện tượng tự cảm và suất điện động tự cảm: Hiện tượng cảm ứng điện từ xảy ra trong chính mạch điện do sự biến thiên của cường độ dòng điện trong mạch đó.")
            c3_formula = "e_tc = - L · (di / dt)   với   L = 4π · 10⁻⁷ · μ · (N² / l) · S"

            core_concepts = [
                {
                    "title": f"Bản chất & Công thức: {short_topic}",
                    "definition": c1_def,
                    "formula": c1_formula,
                    "unit_and_note": "Trong đó: Φ là từ thông (Wb), B là cảm ứng từ (T), S là diện tích mặt cắt (m²), e_c là suất điện động (V).",
                    "tip": "Dấu (-) trong công thức thể hiện định luật Lenz về chiều phản kháng của dòng điện cảm ứng."
                },
                {
                    "title": "Quy tắc xác định chiều & Cường độ dòng điện cảm ứng",
                    "definition": c2_def,
                    "formula": c2_formula,
                    "unit_and_note": "R là điện trở toàn phần của khung dây (Ω), i_c là cường độ dòng cảm ứng (A).",
                    "tip": "Khi từ thông tăng thì B_c ngược chiều B ngoài; khi từ thông giảm thì B_c cùng chiều B ngoài."
                },
                {
                    "title": "Hiện tượng Tự cảm & Hệ số tự cảm L của ống dây",
                    "definition": c3_def,
                    "formula": c3_formula,
                    "unit_and_note": "L là độ tự cảm (Henry - H), N là số vòng dây, l là chiều dài ống dây (m).",
                    "tip": "Suất điện động tự cảm tỉ lệ thuận với tốc độ biến thiên dòng điện di/dt, đóng vai trò quán tính điện từ."
                }
            ]

            # Detailed Example with complete step-by-step
            ex1_problem = get_line(example_lines, 0, "Khung dây tròn đường kính 10 cm, điện trở 0,2 Ω đặt trong từ trường đều có B biến thiên từ 0 đến 0,5 T trong thời gian 0,1 giây.")
            ex_list = [
                {
                    "title": "Bài toán mẫu 1: Tính suất điện động và dòng điện cảm ứng",
                    "problem": ex1_problem,
                    "solution": "Bước 1: Tính diện tích S = π · r² = π · (0,05)² ≈ 7,85 · 10⁻³ m².\nBước 2: Độ biến thiên từ thông ΔΦ = ΔB · S = 0,5 · 7,85 · 10⁻³ ≈ 3,925 · 10⁻³ Wb.\nBước 3: Độ lớn e_c = |ΔΦ / Δt| = 3,925 · 10⁻³ / 0,1 = 0,039 V.\nBước 4: Cường độ i_c = e_c / R = 0,039 / 0,2 ≈ 0,196 A."
                }
            ]
            if len(example_lines) > 1:
                ex_list.append({
                    "title": "Bài toán mẫu 2: Bài toán vận dụng nâng cao",
                    "problem": example_lines[1],
                    "solution": "Áp dụng định luật Faraday kết hợp quy tắc Lenz xác định chính xác chiều vector B_c và thiết lập phương trình vi phân dòng điện."
                })

        else:
            # 3-Minute Quick Mode: Ultra-concise, combined definition & formula, fast identification
            c1_def = get_line(concept_lines, 0, f"Bản chất: Sự biến thiên từ thông sinh ra suất điện động cảm ứng trong mạch kín.")
            c1_formula = "e_c = - dΦ / dt   (Độ lớn: |e_c| = |ΔΦ / Δt|)"

            c2_def = "Định luật Lenz: Dòng điện cảm ứng sinh ra từ trường chống lại sự biến thiên của từ thông ban đầu (Tăng thì chống, giảm thì kéo)."
            c2_formula = "i_c = e_c / R"
            c3_def = "Hiện tượng tự cảm: Khi dòng điện i trong mạch tự biến thiên sinh ra từ thông riêng biến thiên, làm xuất hiện suất điện động tự cảm."
            c3_formula = "e_tc = - L · (di / dt)"

            core_concepts = [
                {
                    "title": f"Định nghĩa & Công thức cốt lõi: {short_topic}",
                    "definition": c1_def,
                    "formula": c1_formula,
                    "unit_and_note": "Đơn vị: Φ (Wb), e_c (V), t (s). Nhớ đổi đơn vị cm → m, cm² → 10⁻⁴ m².",
                    "tip": "Đề thi hay gài bẫy: Cảm ứng từ B biến thiên hoặc Khung dây quay làm thay đổi góc α."
                },
                {
                    "title": "Chiều dòng điện & Công thức dòng cảm ứng",
                    "definition": c2_def,
                    "formula": c2_formula,
                    "unit_and_note": "Quy tắc nắm tay phải: Ngón cái chỉ chiều B_c, các ngón khum chỉ chiều i_c.",
                    "tip": "Quy tắc 3 giây: Φ tăng → B_c ngược B; Φ giảm → B_c cùng B."
                },
                {
                    "title": "Hiện tượng Tự cảm & Suất điện động tự cảm",
                    "definition": c3_def,
                    "formula": c3_formula,
                    "unit_and_note": "L là độ tự cảm (H). Độ lớn: |e_tc| = L · |Δi / Δt|.",
                    "tip": "Quán tính điện: Đóng mạch dòng tăng chậm, ngắt mạch sinh tia lửa điện."
                }
            ]

            ex1_problem = get_line(example_lines, 0, "Cho khung dây S = 50 cm² trong từ trường B giảm đều 0,2 T trong 0,05s. Tính |e_c|.")
            ex_list = [
                {
                    "title": "Dạng bài trắc nghiệm 30 giây: Tính nhanh suất điện động",
                    "problem": ex1_problem,
                    "solution": "|e_c| = S · (ΔB / Δt) = (50 · 10⁻⁴) · (0,2 / 0,05) = 0,02 V. Bấm máy tính trực tiếp không cần vẽ hình."
                }
            ]

        quick_quiz = {
            "question": f"Về mặt định luật và công thức của '{short_topic}', phát biểu nào sau đây là ĐÚNG?",
            "options": [
                "A. Độ lớn của suất điện động cảm ứng tỉ lệ với tốc độ biến thiên của từ thông qua mạch (|e_c| = |dΦ/dt|)",
                "B. Dòng điện cảm ứng luôn có chiều cùng chiều với từ trường ngoài bất kể từ thông tăng hay giảm",
                "C. Suất điện động cảm ứng chỉ xuất hiện khi mạch điện hở và không có điện trở",
                "D. Từ thông qua mạch kín luôn là một hằng số không bao giờ thay đổi theo thời gian"
            ],
            "correct_index": 0,
            "explanation": "Theo Định luật cơ bản của Faraday, độ lớn suất điện động cảm ứng tỉ lệ thuận với tốc độ biến thiên từ thông (|e_c| = |ΔΦ/Δt|). Dấu (-) trong định luật thể hiện quy tắc Lenz."
        }

        advanced_materials = []
        if is_advanced:
            advanced_materials = [
                {
                    "title": f"Dạng bài phân loại điểm 9-10: Thanh kim loại chuyển động cắt đường sức từ",
                    "type": "Vận dụng cao",
                    "description": "Phương trình e = B · v · l · sin(θ). Phân tích lực từ cản trở chuyển động (F_từ = B · I · l) và năng lượng tỏa ra trên điện trở."
                },
                {
                    "title": "Chuyên đề nâng cao: Dòng điện xoáy (Foucault) & Ứng dụng phanh điện từ",
                    "type": "Chuyên sâu",
                    "description": "Cơ chế thất thoát năng lượng do hiệu ứng Joule-Lenz và phương pháp ghép các lá thép kỹ thuật điện để giảm dòng Foucault."
                }
            ]

        return {
            "task_title": task_title,
            "summary_mode": summary_mode,
            "core_concepts": core_concepts,
            "examples": ex_list,
            "quick_quiz": quick_quiz,
            "advanced_materials": advanced_materials
        }

ai_service = AIService()

