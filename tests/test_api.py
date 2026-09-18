from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

init_db()
client = TestClient(app)

def test_load_sample_and_analyze():
    response = client.post("/api/demo/load-sample")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Triết học" in data["subject_name"]
    assert len(data["topics"]) >= 3
    print("✓ Test load sample passed:", data["subject_name"], f"({len(data['topics'])} topics)")
    return data["document_id"]

def test_generate_study_plan():
    doc_id = test_load_sample_and_analyze()
    
    exam_d = (date.today() + timedelta(days=14)).isoformat()
    payload = {
        "document_id": doc_id,
        "exam_date": exam_d,
        "daily_hours": 2.0,
        "target_score": 8.5
    }
    response = client.post("/api/plans/generate", json=payload)
    assert response.status_code == 200
    plan = response.json()
    assert plan["target_score"] == 8.5
    assert len(plan["tasks"]) > 0
    
    # Check that Spaced Repetition tasks exist
    task_types = [t["task_type"] for t in plan["tasks"]]
    assert "study_new" in task_types
    assert "spaced_review" in task_types
    print("✓ Test generate plan passed:", len(plan["tasks"]), "tasks created with spaced repetition!")
    return plan["id"], plan["tasks"][0]["id"]

def test_toggle_task():
    plan_id, task_id = test_generate_study_plan()
    
    # Toggle complete
    res = client.patch(f"/api/tasks/{task_id}/toggle")
    assert res.status_code == 200
    assert res.json()["is_completed"] is True

    # Check updated plan progress
    plan_res = client.get(f"/api/plans/{plan_id}")
    plan = plan_res.json()
    assert plan["completed_tasks"] >= 1
    assert plan["progress_percent"] > 0
    print(f"✓ Test toggle task passed: Progress is {plan['progress_percent']}%")
    return plan_id

def test_reschedule():
    plan_id = test_toggle_task()
    
    res = client.post(f"/api/plans/{plan_id}/reschedule")
    assert res.status_code == 200
    data = res.json()
    assert len(data["tasks"]) > 0
    print("✓ Test reschedule passed: Tasks redistributed cleanly!")

def test_chat_rag():
    doc_id = test_load_sample_and_analyze()
    
    payload = {
        "document_id": doc_id,
        "question": "Vấn đề cơ bản của triết học gồm những mặt nào?"
    }
    res = client.post("/api/chat/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["answer"]) > 20
    assert data["sources_count"] > 0
    print("✓ Test chat RAG passed: Answer returned with relevant syllabus sources!")

def test_export_ical():
    plan_id, _ = test_generate_study_plan()
    res = client.get(f"/api/plans/{plan_id}/export-ical")
    assert res.status_code == 200
    assert "BEGIN:VCALENDAR" in res.text
    assert "BEGIN:VEVENT" in res.text
    print("✓ Test iCal export passed: Valid .ics calendar generated!")

if __name__ == "__main__":
    test_load_sample_and_analyze()
    test_generate_study_plan()
    test_toggle_task()
    test_reschedule()
    test_chat_rag()
    test_export_ical()
    print("\n🎉 ALL UNIT & INTEGRATION TESTS PASSED SUCCESSFULLY!")
