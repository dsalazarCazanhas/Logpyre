from io import BytesIO
from unittest.mock import MagicMock, patch

from elastic_transport import ApiResponseMeta, HttpHeaders
from elasticsearch import ApiError

from logpyre.elastic.search import SearchResult
from logpyre.ingest.pipeline import IngestResult, LineError


def _api_error(message: str = "boom") -> ApiError:
    meta = ApiResponseMeta(status=503, http_version="1.1", headers=HttpHeaders({}), duration=0.0, node=None)
    return ApiError(message, meta, {"error": message})


def _upload_files(filename: str = "access.log", content: bytes = b"some log content"):
    return {"log_file": (BytesIO(content), filename)}


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestIndex:

    def test_renders_the_upload_form(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"log_file" in resp.data


# ---------------------------------------------------------------------------
# GET /api/projects, DELETE /api/projects/<slug>
# ---------------------------------------------------------------------------

class TestApiProjects:

    def test_lists_project_slugs(self, client):
        with patch("logpyre.web.routes.list_projects", return_value=["frontend", "infra"]):
            resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.get_json() == ["frontend", "infra"]


class TestApiDeleteProject:

    def test_invalid_slug_is_rejected_before_touching_elasticsearch(self, client):
        with patch("logpyre.web.routes.delete_project") as mock_delete:
            resp = client.delete("/api/projects/Not-Valid!")
        assert resp.status_code == 400
        mock_delete.assert_not_called()

    def test_reserved_slug_returns_400(self, client):
        with patch("logpyre.web.routes.delete_project", side_effect=ValueError("reserved")):
            resp = client.delete("/api/projects/formats")
        assert resp.status_code == 400

    def test_elasticsearch_error_returns_503(self, client):
        with patch("logpyre.web.routes.delete_project", side_effect=_api_error()):
            resp = client.delete("/api/projects/frontend")
        assert resp.status_code == 503

    def test_no_matching_indices_returns_404(self, client):
        with patch("logpyre.web.routes.delete_project", return_value=0):
            resp = client.delete("/api/projects/ghost")
        assert resp.status_code == 404

    def test_success_returns_deleted_count(self, client):
        with patch("logpyre.web.routes.delete_project", return_value=3):
            resp = client.delete("/api/projects/frontend")
        assert resp.status_code == 200
        assert resp.get_json() == {"deleted_indices": 3}


# ---------------------------------------------------------------------------
# GET /api/search
# ---------------------------------------------------------------------------

class TestApiSearch:

    def test_empty_result_falls_back_to_the_first_registered_parser(self, client):
        empty = SearchResult(hits=[], total=0, page=1, page_size=20)
        with patch("logpyre.web.routes.search_logs", return_value=empty):
            resp = client.get("/api/search")
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["hits"] == []
        assert body["total"] == 0
        assert body["column_defs"]  # falls back to a real registered parser's defs

    def test_hits_resolve_format_metadata_from_the_first_hit(self, client):
        result = SearchResult(
            hits=[{"log_format": "nginx_combined", "raw": "line one"}],
            total=1, page=1, page_size=20,
        )
        with patch("logpyre.web.routes.search_logs", return_value=result), \
             patch("logpyre.web.routes.get_format_metadata", return_value=None):
            resp = client.get("/api/search?q=admin")
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["format_label"] == "Nginx Combined"
        assert body["hits"] == [{"log_format": "nginx_combined", "raw": "line one"}]

    def test_elasticsearch_error_returns_503(self, client):
        with patch("logpyre.web.routes.search_logs", side_effect=_api_error()):
            resp = client.get("/api/search")
        assert resp.status_code == 503

    def test_non_numeric_page_falls_back_to_1(self, client):
        empty = SearchResult(hits=[], total=0, page=1, page_size=20)
        with patch("logpyre.web.routes.search_logs", return_value=empty) as mock_search:
            client.get("/api/search?page=not-a-number")
        assert mock_search.call_args.kwargs["page"] == 1

    def test_page_size_is_capped_at_100(self, client):
        empty = SearchResult(hits=[], total=0, page=1, page_size=20)
        with patch("logpyre.web.routes.search_logs", return_value=empty) as mock_search:
            client.get("/api/search?page_size=500")
        assert mock_search.call_args.kwargs["page_size"] == 100

    def test_repeated_q_params_are_all_passed_as_terms(self, client):
        empty = SearchResult(hits=[], total=0, page=1, page_size=20)
        with patch("logpyre.web.routes.search_logs", return_value=empty) as mock_search:
            client.get("/api/search?q=status:404&q=POST")
        assert mock_search.call_args.kwargs["terms"] == ["status:404", "POST"]


# ---------------------------------------------------------------------------
# GET /api/analytics
# ---------------------------------------------------------------------------

class TestApiAnalytics:

    def test_returns_the_aggregation_buckets(self, client):
        analytics = MagicMock(
            daily_counts=[{"date": "2024-10-04", "count": 5}],
            method_counts=[{"value": "GET", "count": 5}],
            path_counts=[{"value": "/", "count": 5}],
        )
        with patch("logpyre.web.routes.get_analytics", return_value=analytics):
            resp = client.get("/api/analytics")
        assert resp.status_code == 200
        assert resp.get_json() == {
            "daily_counts": [{"date": "2024-10-04", "count": 5}],
            "method_counts": [{"value": "GET", "count": 5}],
            "path_counts": [{"value": "/", "count": 5}],
        }

    def test_elasticsearch_error_returns_503(self, client):
        with patch("logpyre.web.routes.get_analytics", side_effect=_api_error()):
            resp = client.get("/api/analytics")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/formats
# ---------------------------------------------------------------------------

class TestApiFormats:

    def test_lists_registered_formats_with_a_cache_header(self, client):
        resp = client.get("/api/formats")
        assert resp.status_code == 200
        assert resp.headers["Cache-Control"] == "public, max-age=300"
        formats = resp.get_json()
        assert {"format_name": "nginx_combined", "format_label": "Nginx Combined"} in formats


# ---------------------------------------------------------------------------
# GET/POST /upload
# ---------------------------------------------------------------------------

class TestUploadGet:

    def test_renders_the_form(self, client):
        resp = client.get("/upload")
        assert resp.status_code == 200
        assert b"log_file" in resp.data


class TestUploadPost:

    def test_missing_required_fields_re_renders_the_form(self, client):
        resp = client.post("/upload", data={}, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert b"upload" in resp.data.lower()

    def test_invalid_project_slug_is_rejected(self, client):
        resp = client.post(
            "/upload",
            data={"project": "Not-Valid", "log_format": "nginx_combined", **_upload_files()},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert b"lowercase" in resp.data

    def test_existing_project_is_rejected(self, client):
        with patch("logpyre.web.routes.project_exists", return_value=True):
            resp = client.post(
                "/upload",
                data={"project": "frontend", "log_format": "nginx_combined", **_upload_files()},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200
        assert b"already exists" in resp.data

    def test_elasticsearch_down_while_checking_project_existence(self, client):
        with patch("logpyre.web.routes.project_exists", side_effect=Exception("boom")):
            resp = client.post(
                "/upload",
                data={"project": "frontend", "log_format": "nginx_combined", **_upload_files()},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200
        assert b"Elasticsearch" in resp.data

    def test_elasticsearch_down_while_saving_format_metadata(self, client):
        with patch("logpyre.web.routes.project_exists", return_value=False), \
             patch("logpyre.web.routes.upsert_format_metadata", side_effect=_api_error()):
            resp = client.post(
                "/upload",
                data={"project": "frontend", "log_format": "nginx_combined", **_upload_files()},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200
        assert b"Elasticsearch" in resp.data

    def test_full_success_redirects_to_index(self, client):
        result = IngestResult(total=3, indexed=3, failed=0, errors=[])
        with patch("logpyre.web.routes.project_exists", return_value=False), \
             patch("logpyre.web.routes.upsert_format_metadata"), \
             patch("logpyre.web.routes.ingest_file", return_value=result):
            resp = client.post(
                "/upload",
                data={"project": "frontend", "log_format": "nginx_combined", **_upload_files()},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"

    def test_partial_failure_stays_on_the_page_with_error_details(self, client):
        result = IngestResult(
            total=2, indexed=1, failed=1,
            errors=[LineError(line_number=2, raw="bad line", reason="parse error")],
        )
        with patch("logpyre.web.routes.project_exists", return_value=False), \
             patch("logpyre.web.routes.upsert_format_metadata"), \
             patch("logpyre.web.routes.ingest_file", return_value=result):
            resp = client.post(
                "/upload",
                data={"project": "frontend", "log_format": "nginx_combined", **_upload_files()},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200
        assert b"bad line" in resp.data


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:

    def test_reachable_cluster_returns_ok(self, client):
        mock_client = MagicMock()
        with patch("logpyre.web.routes.get_client", return_value=mock_client):
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}

    def test_unreachable_cluster_returns_503(self, client):
        mock_client = MagicMock()
        mock_client.info.side_effect = Exception("connection refused")
        with patch("logpyre.web.routes.get_client", return_value=mock_client):
            resp = client.get("/health")
        assert resp.status_code == 503
        assert resp.get_json()["status"] == "error"


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

class TestErrorHandlers:

    def test_unknown_route_renders_the_404_page(self, client):
        resp = client.get("/this-route-does-not-exist")
        assert resp.status_code == 404

    def test_unhandled_exception_renders_the_500_page(self, client):
        with patch("logpyre.web.routes.search_logs", side_effect=RuntimeError("unexpected")):
            resp = client.get("/api/search")
        assert resp.status_code == 500
