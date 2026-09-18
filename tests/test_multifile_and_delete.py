from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_multifile_upload_and_delete():
    # Create two mock files
    file1_content = "CHƯƠNG 1: TỔNG QUAN VÀ KHÁI NIỆM CƠ BẢN\nĐịnh nghĩa và ý nghĩa môn học.".encode("utf-8")
    file2_content = "CHƯƠNG 2: NGUYÊN LÝ VẬN HÀNH VÀ PHÂN TÍCH\nCác quy luật phát triển.".encode("utf-8")

    files = [
        ("files", ("chuong1.txt", file1_content, "text/plain")),
        ("files", ("chuong2.txt", file2_content, "text/plain"))
    ]

    res = client.post("/api/documents/upload-multiple", files=files)
    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()
    assert data["success"] is True
    doc_id = data["document_id"]
    assert len(data["topics"]) >= 2
    print(f"✓ Multi-file upload: PASSED! Combined {data['files_count']} files, doc_id={doc_id}")

    # Now test delete document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
    print(f"✓ Delete document: PASSED! Deleted doc_id={doc_id}")

    # Verify document no longer exists
    get_res = client.get(f"/api/documents")
    doc_ids = [d["id"] for d in get_res.json()]
    assert doc_id not in doc_ids
    print("✓ Verification: Document verified removed from database!")

def test_google_calendar_ics_upload():
    sample_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
DTSTART:20260921T080000Z
DTEND:20260921T113000Z
SUMMARY:Học Lý Thuyết Mạch
RRULE:FREQ=WEEKLY;BYDAY=MO
END:VEVENT
BEGIN:VEVENT
DTSTART:20260923T130000Z
DTEND:20260923T163000Z
SUMMARY:Thí Nghiệm Vật Lý
RRULE:FREQ=WEEKLY;BYDAY=WE
END:VEVENT
END:VCALENDAR
"""
    files = {"file": ("my_calendar.ics", sample_ics.encode("utf-8"), "text/calendar")}
    res = client.post("/api/timetable/upload", files=files)
    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()
    assert data["success"] is True
    assert "Google Calendar" in data["summary"]
    assert "weekly_schedule" in data
    print("✓ Google Calendar .ics upload: PASSED!", data["summary"])


def test_delete_topic_and_plan_generation():
    # Load sample syllabus with 3 chapters
    res = client.post("/api/demo/load-sample")
    assert res.status_code == 200
    data = res.json()
    doc_id = data["document_id"]
    assert len(data["files_list"]) == 3
    assert data["files_list"][0]["topic_code"] == "CH1"

    # Delete chapter 1 topic
    del_res = client.delete(f"/api/documents/{doc_id}/topics/CH1")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["success"] is True
    print(f"✓ Delete topic CH1: PASSED! Remaining topics: {del_data['remaining_count']}")

    # Generate plan with remaining topic codes (CH2, CH3)
    plan_res = client.post("/api/plans/generate", json={
        "document_id": doc_id,
        "exam_date": "2026-10-30",
        "daily_hours": 1.5,
        "target_score": 8.0,
        "active_topic_codes": ["CH2", "CH3"]
    })
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    # Ensure no tasks mention CH1
    ch1_tasks = [t for t in plan_data["tasks"] if "CH1" in t["title"] or "Chương 1" in t["title"]]
    assert len(ch1_tasks) == 0, f"Found CH1 tasks: {ch1_tasks}"
    print(f"✓ Generate plan with remaining topics: PASSED! {len(plan_data['tasks'])} tasks created, 0 tasks from deleted Chapter 1.")

if __name__ == "__main__":
    test_delete_topic_and_plan_generation()
    test_multifile_upload_and_delete()
    test_google_calendar_ics_upload()
    print("\n🎉 ALL MULTI-FILE, DELETE, AND GOOGLE CALENDAR TESTS PASSED 100%!")
