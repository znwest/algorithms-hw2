import http.client
from contextlib import redirect_stderr
import io
import importlib
from http.server import HTTPServer
import json
import sys
from threading import Thread
import unittest
from unittest.mock import patch

from src import shortener
from src.server import (
    DEFAULT_HOST,
    ShortenerRequestHandler,
    create_server,
    main,
)


class ServerTests(unittest.TestCase):
    def test_public_server_default_binds_all_interfaces(self):
        server = create_server(port=0)
        try:
            self.assertEqual(server.server_address[0], DEFAULT_HOST)
        finally:
            server.server_close()

    def test_port_conflict_suggests_stopping_or_changing_port(self):
        occupied_server = create_server(port=0)
        port = occupied_server.server_port
        stderr = io.StringIO()
        try:
            with (
                patch.object(
                    sys,
                    "argv",
                    ["server", "--port", str(port), "--table", "linear"],
                ),
                redirect_stderr(stderr),
                self.assertRaises(SystemExit) as raised,
            ):
                main()
        finally:
            occupied_server.server_close()

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("이미 사용 중", stderr.getvalue())
        self.assertIn("Ctrl+C", stderr.getvalue())
        self.assertIn("make serve PORT=8001 TABLE=linear", stderr.getvalue())

    def setUp(self):
        importlib.reload(shortener)
        self.server = HTTPServer(("127.0.0.1", 0), ShortenerRequestHandler)
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.getheaders(), response.read()
        connection.close()
        return result

    def test_home_page_has_the_shortening_form(self):
        status, headers, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn(
            ("Content-Type", "text/html; charset=utf-8"),
            headers,
        )
        self.assertIn(b'id="shorten-form"', body)
        self.assertIn(b'fetch("/api/shorten"', body)

    def test_shortening_returns_created_then_existing_response(self):
        request_body = json.dumps({"url": "https://example.com/a"}).encode()
        headers = {"Content-Type": "application/json"}

        first_status, _, first_body = self.request(
            "POST", "/api/shorten", request_body, headers
        )
        second_status, _, second_body = self.request(
            "POST", "/api/shorten", request_body, headers
        )

        self.assertEqual(first_status, 201)
        self.assertEqual(second_status, 200)
        self.assertEqual(json.loads(first_body), json.loads(second_body))
        self.assertEqual(
            json.loads(first_body)["short_url"],
            f"http://localhost:{self.port}/0",
        )

    def test_short_link_redirects_to_original_url(self):
        original_url = "https://example.com/path?x=1"
        shortener.shorten(original_url)

        status, headers, _ = self.request("GET", "/0?from=browser")

        self.assertEqual(status, 302)
        self.assertIn(("Location", original_url), headers)

    def test_table_shows_bucket_node_and_expandable_horner_steps(self):
        url = 'https://example.com/?q="<tag>"'
        shortener.shorten(url)

        status, headers, body = self.request("GET", "/table")
        page = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn(("Content-Type", "text/html; charset=utf-8"), headers)
        self.assertIn("URL 키", page)
        self.assertIn("짧은 코드", page)
        self.assertIn("http://localhost:", page)
        self.assertIn("<details>", page)
        self.assertIn("mod 8", page)
        self.assertIn('id="linear-probing-table"', page)
        self.assertIn("선형 탐지 순서와 비교 근거 펼치기", page)
        self.assertIn("mod 8 =", page)
        self.assertIn("&quot;&lt;tag&gt;&quot;", page)

    def test_invalid_payload_and_unknown_routes_have_expected_status(self):
        status, headers, body = self.request(
            "POST",
            "/api/shorten",
            b"[]",
            {"Content-Length": "2"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(
            dict(headers)["Content-Type"],
            "application/json; charset=utf-8",
        )
        self.assertIn(b"error", body)

        self.assertEqual(self.request("GET", "/api/shorten")[0], 405)
        self.assertEqual(self.request("GET", "/missing")[0], 404)
        self.assertEqual(self.request("POST", "/unknown")[0], 404)

    def test_oversized_body_is_rejected_before_reading(self):
        status, _, _ = self.request(
            "POST",
            "/api/shorten",
            headers={"Content-Length": "8193"},
        )

        self.assertEqual(status, 413)


if __name__ == "__main__":
    unittest.main()
