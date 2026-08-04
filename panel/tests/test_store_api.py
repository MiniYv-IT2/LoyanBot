"""插件商店后端接口对齐测试 — 聚合字段 / 点赞 / 配置 / 服务器端到端"""

import httpx
import logging

PANEL_URL = "http://127.0.0.1:5090"
STATS_URL = "http://38.55.145.10:16385"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_store_api")

REQUIRED_FIELDS = [
    "id", "name", "author", "description", "category", "tags",
    "likes", "downloads", "installed", "update_available",
    "icon", "docs_url", "repo", "version", "source",
]


def test_store_plugins_fields():
    with httpx.Client(timeout=30) as c:
        resp = c.get(f"{PANEL_URL}/api/loyanui/store/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        plugins = data["data"]
        assert len(plugins) > 0, "插件列表不应为空"
        p = plugins[0]
        for field in REQUIRED_FIELDS:
            assert field in p, f"缺少字段: {field}"
        assert isinstance(p["likes"], int)
        assert isinstance(p["downloads"], int)
        assert isinstance(p["tags"], list)
        logger.info(f"插件样例: {p['id']} likes={p['likes']} downloads={p['downloads']} cat={p['category']}")


def test_store_config():
    with httpx.Client(timeout=10) as c:
        resp = c.get(f"{PANEL_URL}/api/loyanui/store/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        cfg = data["data"]
        assert "sources" in cfg and isinstance(cfg["sources"], list)
        assert "git_mirrors" in cfg
        assert "stats_url" in cfg
        logger.info(f"源: {[s['name'] for s in cfg['sources']]} stats_url={cfg['stats_url']}")


def test_store_like():
    with httpx.Client(timeout=15) as c:
        resp = c.post(f"{PANEL_URL}/api/loyanui/store/plugins/Music_Plugin/like")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        logger.info("点赞接口 OK")


def test_stats_server_end_to_end():
    with httpx.Client(timeout=10) as c:
        store = c.get(f"{STATS_URL}/store.json")
        assert store.status_code == 200
        plugins = store.json().get("plugins", [])
        assert len(plugins) > 0, "服务器插件源不应为空"
        likes = c.get(f"{STATS_URL}/likes")
        assert likes.status_code == 200
        assert isinstance(likes.json(), dict)
        downloads = c.get(f"{STATS_URL}/downloads")
        assert downloads.status_code == 200
        assert isinstance(downloads.json(), dict)
        logger.info(f"服务器源插件数: {len(plugins)}; likes: {likes.json()}; downloads: {downloads.json()}")
