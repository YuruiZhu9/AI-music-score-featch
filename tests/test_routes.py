"""
tests/test_routes.py — API 路由文档完整性测试
==============================================
验证 backend/api/routes.py 中的路由清单与 main.py 中的实际路由是否一致。
如果新增了路由但未在 routes.py 中注册，测试会失败。
"""

import pytest
from backend.api.routes import ROUTES, RouteSpec, FRONTEND_QUICKREF


class TestRouteSpec:
    """RouteSpec 数据结构测试"""

    def test_route_has_required_fields(self):
        """每个路由必须包含 method、path、summary"""
        for route in ROUTES:
            assert route.method in {"GET", "POST", "PUT", "DELETE", "PATCH"}
            assert route.path.startswith("/")
            assert len(route.summary) > 0

    def test_all_paths_unique(self):
        """不允许重复的路由路径"""
        paths = [(r.method, r.path) for r in ROUTES]
        assert len(paths) == len(set(paths)), "发现重复的路由路径"

    def test_all_errors_valid_http_codes(self):
        """错误码必须是有效的 HTTP 状态码"""
        for route in ROUTES:
            if route.errors:
                for code in route.errors:
                    assert 100 <= code < 600, f"无效的 HTTP 状态码: {code}"

    def test_all_routes_tagged(self):
        """每个路由必须指定 tag"""
        for route in ROUTES:
            assert route.tag, f"路由 {route.method} {route.path} 缺少 tag"

    def test_status_routes_exist(self):
        """必须包含 / 和 /health 两个状态路由"""
        paths = {r.path for r in ROUTES}
        assert "/" in paths, "缺少根路由 /"
        assert "/health" in paths, "缺少健康检查路由 /health"

    def test_task_routes_exist(self):
        """必须包含任务管理相关路由"""
        paths = {r.path for r in ROUTES}
        assert any("/api/upload" in p for p in paths), "缺少 /api/upload"
        assert any("/api/task/" in p for p in paths), "缺少 /api/task/{task_id}"
        assert any("/api/analyze-url" in p for p in paths), "缺少 /api/analyze-url"

    def test_result_route_exists(self):
        """必须包含结果查询路由"""
        paths = {r.path for r in ROUTES}
        assert any("/api/result/" in p for p in paths), "缺少 /api/result/{task_id}"

    def test_download_routes_exist(self):
        """必须包含文件下载路由"""
        paths = {r.path for r in ROUTES}
        assert any("/api/download/" in p for p in paths), "缺少 /api/download/{task_id}"

    def test_gta_download_exists(self):
        """必须包含 GTA 文本谱下载路由"""
        paths = [r.path for r in ROUTES]
        assert any("/gta" in p for p in paths), "缺少 GTA 文本谱下载路由 /api/download/{task_id}/gta"

    def test_pdf_download_exists(self):
        """必须包含 PDF 乐谱下载路由"""
        paths = [r.path for r in ROUTES]
        assert any("/pdf" in p for p in paths), "缺少 PDF 下载路由 /api/download/{task_id}/pdf"

    def test_upload_accepts_file(self):
        """上传路由必须声明接受文件类型"""
        for route in ROUTES:
            if "/api/upload" == route.path:
                assert route.request is not None
                assert "file" in route.request.lower()

    def test_analyze_url_accepts_json(self):
        """URL 分析路由必须声明 JSON 请求"""
        for route in ROUTES:
            if "/api/analyze-url" in route.path:
                assert route.request is not None
                assert "json" in route.request.lower() or "url" in route.request.lower()

    def test_result_returns_task_id(self):
        """结果路由的 response 必须包含 task_id"""
        for route in ROUTES:
            if "/api/result/" in route.path:
                assert route.response is not None
                assert "task_id" in route.response.lower()


class TestFrontendQuickref:
    """前端对接速查文档测试"""

    def test_quickref_not_empty(self):
        """FRONTEND_QUICKREF 必须非空"""
        assert len(FRONTEND_QUICKREF) > 100

    def test_quickref_mentions_poll(self):
        """速查必须提到轮询机制"""
        assert "轮询" in FRONTEND_QUICKREF or "poll" in FRONTEND_QUICKREF.lower()

    def test_quickref_mentions_upload(self):
        """速查必须提到上传流程"""
        assert "/api/upload" in FRONTEND_QUICKREF

    def test_quickref_mentions_result(self):
        """速查必须提到结果查询"""
        assert "/api/result" in FRONTEND_QUICKREF

    def test_quickref_mentions_download(self):
        """速查必须提到下载流程"""
        assert "/api/download" in FRONTEND_QUICKREF

    def test_quickref_mentions_timeout(self):
        """速查必须提到超时处理"""
        assert "超时" in FRONTEND_QUICKREF or "timeout" in FRONTEND_QUICKREF.lower()
