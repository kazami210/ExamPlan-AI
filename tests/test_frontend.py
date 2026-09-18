from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
r_index = client.get("/")
assert r_index.status_code == 200
assert "ExamPlan AI" in r_index.text
print("✓ Index page served successfully!")

r_css = client.get("/static/styles.css")
assert r_css.status_code == 200
assert "primary" in r_css.text
print("✓ CSS file served successfully!")

r_js = client.get("/static/app.js")
assert r_js.status_code == 200
assert "ExamPlan AI" in r_js.text
print("✓ JS file served successfully!")
