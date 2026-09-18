import os
import sys
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8000))
    is_dev = os.environ.get("RENDER") is None

    print("=" * 65)
    print(" ExamPlan AI - Nen tang On thi Dai hoc Ca nhan hoa")
    print(f" Server running at: http://{host}:{port}")
    print("=" * 65)
    uvicorn.run("backend.main:app", host=host, port=port, reload=is_dev)
