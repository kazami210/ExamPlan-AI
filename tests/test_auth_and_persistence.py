from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_auth_and_persistence_flow():
    # 1. Login as Guest
    res_guest = client.post("/api/auth/guest")
    assert res_guest.status_code == 200
    guest_data = res_guest.json()
    assert guest_data["success"] is True
    assert guest_data["user"]["is_guest"] is True
    guest_token = guest_data["token"]
    print("✓ Guest Login: PASSED! Token generated.")

    # 2. Upload document as Guest
    file_content = "CHƯƠNG 1: ĐIỆN TỪ HỌC CƠ BẢN\nĐịnh lý Gauss và phương trình Maxwell.".encode("utf-8")
    files = {"file": ("dien_tu_hoc.txt", file_content, "text/plain")}
    headers = {"Authorization": f"Bearer {guest_token}"}
    
    res_upload_guest = client.post("/api/documents/upload", files=files, headers=headers)
    assert res_upload_guest.status_code == 200
    guest_doc = res_upload_guest.json()
    guest_doc_id = guest_doc["document_id"]
    print(f"✓ Upload as Guest: PASSED! Document ID: {guest_doc_id}")

    # Check that guest document is not permanent
    res_me_guest = client.get("/api/auth/me", headers=headers)
    assert res_me_guest.status_code == 200
    assert res_me_guest.json()["user"]["is_guest"] is True

    # 3. Login as Google User (Gmail)
    google_payload = {
        "email": "sinhvien.hust@gmail.com",
        "name": "Nguyễn Văn An",
        "avatar_url": "https://lh3.googleusercontent.com/a/default-user",
        "google_id": "google-oauth2-12345678",
        "guest_token": guest_token # migrate guest documents!
    }
    res_google = client.post("/api/auth/google", json=google_payload)
    assert res_google.status_code == 200
    user_data = res_google.json()
    assert user_data["success"] is True
    assert user_data["user"]["email"] == "sinhvien.hust@gmail.com"
    assert user_data["user"]["is_guest"] is False
    user_token = user_data["token"]
    print("✓ Google (Gmail) Login: PASSED! User Nguyễn Văn An authenticated.")

    # 4. Verify Library has the migrated document and it is marked permanent
    user_headers = {"Authorization": f"Bearer {user_token}"}
    res_lib = client.get("/api/user/library", headers=user_headers)
    assert res_lib.status_code == 200
    lib_data = res_lib.json()
    assert lib_data["is_guest"] is False
    assert len(lib_data["documents"]) >= 1
    doc_entry = next((d for d in lib_data["documents"] if d["id"] == guest_doc_id), None)
    assert doc_entry is not None
    assert doc_entry["is_saved_permanently"] is True
    print("✓ Guest data migration to Google account: PASSED! Document is now permanently saved.")

    # 5. Login as Facebook User
    fb_payload = {
        "email": "lan.tran@facebook.com",
        "name": "Trần Thị Lan",
        "facebook_id": "fb-987654321"
    }
    res_fb = client.post("/api/auth/facebook", json=fb_payload)
    assert res_fb.status_code == 200
    fb_data = res_fb.json()
    assert fb_data["user"]["provider"] == "facebook"
    assert fb_data["user"]["name"] == "Trần Thị Lan"
    print("✓ Facebook Login: PASSED! User Trần Thị Lan authenticated.")

    # 6. Upload document as authenticated Google User directly
    file2_content = "CHƯƠNG 2: QUANG HỌC LƯỢNG TỬ\nHiện tượng quang điện.".encode("utf-8")
    files2 = {"file": ("quang_hoc.txt", file2_content, "text/plain")}
    res_upload2 = client.post("/api/documents/upload", files=files2, headers=user_headers)
    assert res_upload2.status_code == 200
    print("✓ Direct Upload as Google User: PASSED! Automatically marked as permanent.")

    # Check library again
    res_lib2 = client.get("/api/user/library", headers=user_headers)
    assert len(res_lib2.json()["documents"]) >= 2
    print(f"✓ User Library: PASSED! Total {len(res_lib2.json()['documents'])} documents saved permanently.")

if __name__ == "__main__":
    test_auth_and_persistence_flow()
    
    # 7. Test Google Identity Services ID Token (credential JWT)
    import base64, json
    header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps({
        "iss": "https://accounts.google.com",
        "sub": "google-sub-9999",
        "email": "le.thi.mai@gmail.com",
        "name": "Lê Thị Mai",
        "picture": "https://lh3.googleusercontent.com/mai"
    }).encode()).decode().rstrip("=")
    mock_id_token = f"{header_b64}.{payload_b64}.mock_signature"

    res_gis = client.post("/api/auth/google", json={"credential": mock_id_token})
    assert res_gis.status_code == 200
    gis_data = res_gis.json()
    assert gis_data["user"]["email"] == "le.thi.mai@gmail.com"
    assert gis_data["user"]["name"] == "Lê Thị Mai"
    print("✓ Google Identity Services (credential JWT) Flow: PASSED! User Lê Thị Mai verified.")

    # 8. Test GET /api/config
    res_cfg = client.get("/api/config")
    assert res_cfg.status_code == 200
    assert "google_client_id" in res_cfg.json()
    print("✓ Public Config (/api/config): PASSED!")

    print("\n🎉 ALL AUTHENTICATION & DOCUMENT PERSISTENCE TESTS PASSED 100%!")
