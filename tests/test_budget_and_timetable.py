from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_budget_hard_cap_1h():
    """Ensure that 1.0h/day never produces > 60 minutes on ANY day."""
    # 1. Load sample
    res = client.post("/api/demo/load-sample")
    assert res.status_code == 200
    doc_id = res.json()["document_id"]

    # 2. Generate with 1.0h
    exam_d = (date.today() + timedelta(days=14)).isoformat()
    plan_res = client.post("/api/plans/generate", json={
        "document_id": doc_id,
        "exam_date": exam_d,
        "daily_hours": 1.0,
        "target_score": 8.0
    })
    assert plan_res.status_code == 200
    tasks = plan_res.json()["tasks"]
    
    # Group by date
    from collections import defaultdict
    mins_by_date = defaultdict(int)
    for t in tasks:
        mins_by_date[t["study_date"]] += t["estimated_minutes"]

    for d, total in mins_by_date.items():
        assert total <= 60, f"FAILED: Day {d} has {total} minutes, exceeding 60m budget!"
    print("✓ Test 1h/day budget hard cap: PASSED! Every single day is <= 60 minutes.")

def test_weekly_timetable_custom():
    """Ensure custom weekly schedule (e.g. Sunday = 0h) respects days off."""
    res = client.post("/api/demo/load-sample")
    doc_id = res.json()["document_id"]

    exam_d = (date.today() + timedelta(days=14)).isoformat()
    weekly = {
        "mon": 1.0,
        "tue": 1.0,
        "wed": 1.0,
        "thu": 1.0,
        "fri": 1.0,
        "sat": 2.0,
        "sun": 0.0  # Sunday rest day
    }
    plan_res = client.post("/api/plans/generate", json={
        "document_id": doc_id,
        "exam_date": exam_d,
        "daily_hours": 1.0,
        "target_score": 8.0,
        "weekly_schedule": weekly
    })
    assert plan_res.status_code == 200
    tasks = plan_res.json()["tasks"]

    # Verify no tasks on Sunday
    for t in tasks:
        task_date = date.fromisoformat(t["study_date"])
        assert task_date.weekday() != 6, f"FAILED: Found task scheduled on Sunday {task_date}!"
    print("✓ Test weekly timetable: PASSED! Sunday is respected as rest day (0 tasks).")

def test_timetable_upload():
    """Test timetable upload endpoint."""
    sample_tkb = "Thời khóa biểu: Thứ 2 học sáng 4 tiết; Thứ 3 học chiều; Thứ 7 rảnh cả ngày; Chủ nhật nghỉ."
    files = {"file": ("tkb.txt", sample_tkb.encode("utf-8"), "text/plain")}
    res = client.post("/api/timetable/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "weekly_schedule" in data
    print("✓ Test timetable upload: PASSED!", data["weekly_schedule"])

if __name__ == "__main__":
    test_budget_hard_cap_1h()
    test_weekly_timetable_custom()
    test_timetable_upload()
    print("\n🎉 ALL TIMETABLE & BUDGET CAP TESTS PASSED 100%!")
