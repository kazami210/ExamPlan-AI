import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

WEEKDAY_MAP = {
    0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"
}

ICAL_BYDAY_MAP = {
    "MO": "mon", "TU": "tue", "WE": "wed", "TH": "thu", "FR": "fri", "SA": "sat", "SU": "sun"
}

class TimetableService:
    @classmethod
    def parse_file(cls, filename: str, content: bytes) -> Dict[str, Any]:
        """Automatically detect file type (.ics or text/doc) and parse timetable."""
        ext = Path(filename).suffix.lower()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8-sig", errors="replace")

        if ext == ".ics" or "BEGIN:VCALENDAR" in text:
            return cls.parse_ical_calendar(text)
        else:
            return cls.parse_timetable_text(text)

    @classmethod
    def parse_ical_calendar(cls, ical_text: str) -> Dict[str, Any]:
        """Parse Google Calendar .ics export file and calculate daily free study hours."""
        schedule = {
            "mon": 2.5, "tue": 2.5, "wed": 2.5, "thu": 2.5, "fri": 2.5, "sat": 3.0, "sun": 1.0
        }
        busy_hours_per_day = {k: 0.0 for k in schedule.keys()}
        event_count = 0
        event_summaries = []

        # Split into VEVENT blocks
        events = re.findall(r"BEGIN:VEVENT([\s\S]*?)END:VEVENT", ical_text)
        for ev in events:
            event_count += 1
            # Extract summary
            summ_match = re.search(r"SUMMARY:(.+)", ev)
            summary = summ_match.group(1).strip() if summ_match else "Sự kiện lịch"
            
            # Extract DTSTART & DTEND
            dtstart_match = re.search(r"DTSTART(?:;[^:]+)?:(\d{8}(?:T\d{6}Z?)?)", ev)
            dtend_match = re.search(r"DTEND(?:;[^:]+)?:(\d{8}(?:T\d{6}Z?)?)", ev)
            rrule_match = re.search(r"RRULE:([^\r\n]+)", ev)

            duration_hours = 1.5 # default estimated event duration
            event_weekday = None

            if dtstart_match:
                val = dtstart_match.group(1)
                try:
                    if "T" in val:
                        dt = datetime.strptime(val[:15].replace("Z", ""), "%Y%m%dT%H%M%S")
                        event_weekday = WEEKDAY_MAP.get(dt.weekday())
                        if dtend_match:
                            end_val = dtend_match.group(1)
                            dt_end = datetime.strptime(end_val[:15].replace("Z", ""), "%Y%m%dT%H%M%S")
                            diff = (dt_end - dt).total_seconds() / 3600.0
                            if 0 < diff < 12:
                                duration_hours = diff
                    else:
                        dt = datetime.strptime(val[:8], "%Y%m%d")
                        event_weekday = WEEKDAY_MAP.get(dt.weekday())
                        duration_hours = 3.0 # all day or multiple hours
                except Exception:
                    pass

            # Handle recurring BYDAY
            if rrule_match and "BYDAY=" in rrule_match.group(1):
                bydays = re.findall(r"(?:MO|TU|WE|TH|FR|SA|SU)", rrule_match.group(1))
                for bd in bydays:
                    code = ICAL_BYDAY_MAP.get(bd)
                    if code:
                        busy_hours_per_day[code] += duration_hours
            elif event_weekday:
                busy_hours_per_day[event_weekday] += duration_hours

            if len(event_summaries) < 4 and summary:
                event_summaries.append(summary)

        # Calculate free hours: 16 waking hours - 8h base activities - busy hours
        for day_code, busy_h in busy_hours_per_day.items():
            if day_code == "sun":
                # By default Sunday is rest / light review
                schedule[day_code] = 0.0 if busy_h > 0 else 0.5
            else:
                # If busy >= 5h -> free ~1.0h; if busy 2-4h -> free ~2.0h; if busy < 2h -> free ~3.0h
                if busy_h >= 6.0:
                    schedule[day_code] = 1.0
                elif busy_h >= 3.0:
                    schedule[day_code] = 1.5
                elif busy_h >= 1.0:
                    schedule[day_code] = 2.0
                else:
                    schedule[day_code] = 2.5 if day_code != "sat" else 3.5

        summ_text = f"Đã đọc Google Calendar ({event_count} sự kiện: {', '.join(event_summaries[:3])}). Tự động tính toán các khung giờ rảnh tối ưu."
        return {
            "success": True,
            "weekly_schedule": schedule,
            "summary": summ_text,
            "event_count": event_count
        }

    @classmethod
    def parse_timetable_text(cls, text: str) -> Dict[str, Any]:
        """Analyze timetable text or exported schedule."""
        schedule = {
            "mon": 2.0, "tue": 2.0, "wed": 2.0, "thu": 2.0, "fri": 2.0, "sat": 3.0, "sun": 0.0
        }
        busy_summary = []

        day_keywords = {
            "mon": [r"thứ\s*2", r"thứ\s*hai", r"monday", r"t2\b"],
            "tue": [r"thứ\s*3", r"thứ\s*ba", r"tuesday", r"t3\b"],
            "wed": [r"thứ\s*4", r"thứ\s*tư", r"wednesday", r"t4\b"],
            "thu": [r"thứ\s*5", r"thứ\s*năm", r"thursday", r"t5\b"],
            "fri": [r"thứ\s*6", r"thứ\s*sáu", r"friday", r"t6\b"],
            "sat": [r"thứ\s*7", r"thứ\s*bảy", r"saturday", r"t7\b"],
            "sun": [r"chủ\s*nhật", r"sunday", r"cn\b"]
        }

        lines = [l.strip() for l in text.split("\n") if l.strip()]

        for day_code, patterns in day_keywords.items():
            day_matches = 0
            for line in lines:
                for pat in patterns:
                    if re.search(pat, line, re.I):
                        day_matches += 1
                        if any(w in line.lower() for w in ["cả ngày", "full", "sáng và chiều", "tiết 1-10", "tiết 1-12"]):
                            schedule[day_code] = 1.0
                            busy_summary.append(f"{day_code.upper()}: Bận cả ngày")
                        elif any(w in line.lower() for w in ["sáng", "tiết 1-5", "tiết 1-6"]):
                            schedule[day_code] = 1.5
                            busy_summary.append(f"{day_code.upper()}: Học ca sáng")
                        elif any(w in line.lower() for w in ["chiều", "tiết 7-11", "tiết 7-12"]):
                            schedule[day_code] = 1.5
                            busy_summary.append(f"{day_code.upper()}: Học ca chiều")

            if day_matches >= 3:
                schedule[day_code] = max(0.5, schedule[day_code] - 0.5)

        return {
            "success": True,
            "weekly_schedule": schedule,
            "summary": "; ".join(busy_summary) if busy_summary else "Đã phân tích thời khóa biểu và tính toán giờ rảnh tối ưu."
        }

timetable_service = TimetableService()
