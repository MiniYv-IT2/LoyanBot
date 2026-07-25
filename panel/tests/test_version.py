"""LoyanUI 版本接口测试"""

import httpx

PANEL_URL = "http://127.0.0.1:5090"


def test_version():
    with httpx.Client() as c:
        resp = c.get(f"{PANEL_URL}/api/loyanui/version")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        version = data["data"]["version"]
        assert isinstance(version, str)
        assert len(version) > 0
        assert version.count(".") >= 2
