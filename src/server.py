"""HTTP interface for the in-memory URL shortener."""

import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlsplit

from src import shortener
from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


DEFAULT_HOST = "0.0.0.0"


HOME_PAGE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>URL 단축기</title>
  <style>
    body { font: 16px system-ui, sans-serif; margin: 3rem auto; max-width: 42rem; padding: 0 1rem; }
    input { box-sizing: border-box; padding: .7rem; width: 100%; }
    button { cursor: pointer; margin-top: .75rem; padding: .65rem 1rem; }
    #result { margin-top: 1.5rem; overflow-wrap: anywhere; }
    nav { margin-top: 2rem; }
  </style>
</head>
<body>
  <main>
    <h1>URL 단축기</h1>
    <form id="shorten-form">
      <label for="url">줄일 URL</label>
      <input id="url" name="url" type="url" required>
      <button type="submit">줄이기</button>
    </form>
    <p id="result" aria-live="polite"></p>
    <nav><a href="/table">해시 테이블 보기</a></nav>
  </main>
  <script>
    const form = document.getElementById("shorten-form");
    const result = document.getElementById("result");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      result.textContent = "처리 중...";
      try {
        const response = await fetch("/api/shorten", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: form.elements.url.value })
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "요청에 실패했습니다.");
        }
        const link = document.createElement("a");
        link.href = data.short_url;
        link.textContent = data.short_url;
        result.replaceChildren(link);
      } catch (error) {
        result.textContent = error.message;
      }
    });
  </script>
</body>
</html>
"""


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    def _send_response(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, str]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_response(
            status,
            body,
            "application/json; charset=utf-8",
        )

    def _send_error_json(
        self,
        status: int,
        message: str,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self._send_response(
            status,
            body,
            "application/json; charset=utf-8",
            extra_headers,
        )

    def _short_url(self, code: str) -> str:
        port = self.server.server_address[1]
        return f"http://localhost:{port}/{code}"

    def _table_page(self) -> bytes:
        buckets = shortener.url_table_snapshot()
        capacity = len(buckets)
        linear_slots = shortener.linear_table_snapshot()
        linear_capacity = len(linear_slots)
        parts = [
            "<!doctype html>",
            '<html lang="ko"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>현재 해시 테이블</title>",
            """<style>
              body { font: 15px system-ui, sans-serif; margin: 2rem auto;
                     max-width: 90rem; padding: 0 1rem; }
              table { border-collapse: collapse; width: 100%; }
              th, td { border: 1px solid #bbb; padding: .65rem; text-align: left;
                       vertical-align: top; }
              th { background: #f2f4f7; }
              .chain { align-items: flex-start; display: flex; flex-wrap: wrap;
                       gap: .6rem; }
              .node { border: 1px solid #7d8b99; border-radius: .35rem;
                      max-width: 34rem; overflow-wrap: anywhere; padding: .7rem; }
              .arrow { align-self: center; font-size: 1.3rem; }
              .empty { color: #777; }
              details { margin-top: .6rem; }
              code { overflow-wrap: anywhere; }
            </style></head><body>""",
            "<h1>현재 해시 테이블</h1>",
            '<p><a href="#chaining-table">체이닝 방식</a> · '
            '<a href="#linear-probing-table">선형 탐지 방식</a></p>',
            '<p><a href="/">URL 단축기로 돌아가기</a></p>',
            '<h2 id="chaining-table">개별 체이닝</h2>',
            '<p>URL 키를 호너 방식으로 해시한 버킷과 연결 리스트입니다.</p>',
            "<table><thead><tr><th>칸</th><th>연결 리스트 (head → tail)</th>",
            "</tr></thead><tbody>",
        ]

        for bucket_index, bucket in enumerate(buckets):
            parts.append(
                f"<tr><th scope=\"row\">{bucket_index}</th><td>"
            )
            if not bucket:
                parts.append('<span class="empty">비어 있음</span>')
            else:
                parts.append('<div class="chain">')
                for node_index, (url, code) in enumerate(bucket):
                    if node_index:
                        parts.append('<span class="arrow" aria-hidden="true">→</span>')
                    safe_url = html.escape(url, quote=True)
                    short_url = html.escape(self._short_url(code), quote=True)
                    parts.extend(
                        [
                            '<section class="node">',
                            f"<p><strong>URL 키</strong>: <code>{safe_url}</code></p>",
                            f"<p><strong>짧은 코드</strong>: <code>{code}</code></p>",
                            f'<p><strong>짧은 링크</strong>: <a href="{short_url}">'
                            f"{short_url}</a></p>",
                            self._hash_details(url, capacity, bucket_index),
                            "</section>",
                        ]
                    )
                parts.append("</div>")
            parts.append("</td></tr>")

        parts.extend(
            [
                "</tbody></table>",
                '<h2 id="linear-probing-table">선형 탐지</h2>',
                '<p>충돌하면 다음 칸으로 이동하고, 마지막 칸 다음에는 0번 칸으로 '
                "돌아갑니다.</p>",
                "<table><thead><tr><th>칸</th><th>저장된 항목</th></tr></thead><tbody>",
            ]
        )
        for slot_index, entry in enumerate(linear_slots):
            parts.append(
                f"<tr><th scope=\"row\">{slot_index}</th><td>"
            )
            if entry is None:
                parts.append('<span class="empty">비어 있음</span>')
            else:
                url, code = entry
                safe_url = html.escape(url, quote=True)
                safe_code = html.escape(code, quote=True)
                short_url = html.escape(self._short_url(code), quote=True)
                parts.extend(
                    [
                        '<section class="node">',
                        f"<p><strong>URL 키</strong>: <code>{safe_url}</code></p>",
                        f"<p><strong>짧은 코드</strong>: <code>{safe_code}</code></p>",
                        f'<p><strong>짧은 링크</strong>: <a href="{short_url}">'
                        f"{short_url}</a></p>",
                        self._hash_details(
                            url,
                            linear_capacity,
                            shortener.linear_probe_indices(url)[0],
                        ),
                        self._linear_probe_details(
                            url, linear_capacity, slot_index, linear_slots
                        ),
                        "</section>",
                    ]
                )
            parts.append("</td></tr>")
        parts.extend(["</tbody></table></body></html>"])
        return "\n".join(parts).encode("utf-8")

    @staticmethod
    def _hash_details(key: str, capacity: int, bucket_index: int) -> str:
        value = 0
        steps = []
        for character in key:
            previous = value
            value = (value * 31 + ord(character)) % capacity
            safe_character = html.escape(character)
            steps.append(
                "<li>"
                f"'{safe_character}' (ord={ord(character)}): "
                f"({previous} × 31 + {ord(character)}) mod {capacity} = {value}"
                "</li>"
            )
        return (
            "<details><summary>호너 해시 계산 펼치기 "
                f"(호너 해시 결과: {bucket_index})</summary>"
            f"<p>h₀ = 0, 문자 수 = {len(key)}</p><ol>{''.join(steps)}</ol></details>"
        )

    @staticmethod
    def _linear_probe_details(
        key: str,
        capacity: int,
        target_index: int,
        slots: tuple[tuple[str, str] | None, ...],
    ) -> str:
        indices = shortener.linear_probe_indices(key)
        home_index = indices[0]
        steps = []
        for offset, slot_index in enumerate(indices):
            entry = slots[slot_index]
            if slot_index == target_index:
                comparison = "URL 키가 일치합니다."
            elif entry is None:
                comparison = "빈 칸입니다."
            else:
                comparison = (
                    "이미 저장된 URL 키 "
                    f"<code>{html.escape(entry[0], quote=True)}</code>와 다릅니다."
                )
            steps.append(
                "<li>"
                f"({home_index} + {offset}) mod {capacity} = {slot_index}: "
                f"{comparison}</li>"
            )
        return (
            "<details><summary>선형 탐지 순서와 비교 근거 펼치기</summary>"
            f"<p>시작 칸 h = {home_index}; 다음 칸은 (h + i) mod {capacity}입니다.</p>"
            f"<ol>{''.join(steps)}</ol></details>"
        )

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_response(
                200,
                HOME_PAGE.encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if path == "/table":
            self._send_response(
                200,
                self._table_page(),
                "text/html; charset=utf-8",
            )
            return
        if path == "/api/shorten":
            self._send_error_json(
                405,
                "POST 메서드로 요청해야 합니다.",
                (("Allow", "POST"),),
            )
            return
        if not path.startswith("/") or path == "/":
            self._send_error_json(404, "요청한 경로를 찾을 수 없습니다.")
            return

        code = path[1:]
        try:
            url = shortener.expand(code)
        except KeyError:
            self._send_error_json(404, "짧은 링크를 찾을 수 없습니다.")
            return

        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/shorten":
            self._send_error_json(404, "요청한 경로를 찾을 수 없습니다.")
            return

        content_length_header = self.headers.get("Content-Length")
        try:
            content_length = int(content_length_header or "")
        except ValueError:
            self._send_error_json(400, "Content-Length가 올바르지 않습니다.")
            return
        if content_length < 0:
            self._send_error_json(400, "Content-Length가 올바르지 않습니다.")
            return
        if content_length > 8192:
            self._send_error_json(413, "요청 본문은 8192바이트 이하여야 합니다.")
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error_json(400, "JSON 본문이 올바르지 않습니다.")
            return
        if not isinstance(payload, dict):
            self._send_error_json(400, "JSON 객체를 보내야 합니다.")
            return
        if "url" not in payload:
            self._send_error_json(400, "url 항목이 필요합니다.")
            return
        if not isinstance(payload["url"], str):
            self._send_error_json(400, "url은 문자열이어야 합니다.")
            return

        try:
            code, is_new = shortener.shorten(payload["url"])
        except ValueError as error:
            self._send_error_json(400, str(error))
            return

        self._send_json(
            201 if is_new else 200,
            {
                "code": code,
                "short_url": self._short_url(code),
            },
        )


def create_server(host: str = DEFAULT_HOST, port: int = 8000) -> HTTPServer:
    return HTTPServer((host, port), ShortenerRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--table",
        choices=("chaining", "linear"),
        default="chaining",
        help="table implementation used by the shortener",
    )
    args = parser.parse_args()

    table_class = (
        HashTable if args.table == "chaining" else LinearProbingHashTable
    )
    shortener.configure_table_type(table_class)
    server = create_server(args.host, args.port)
    display_host = "127.0.0.1" if args.host == DEFAULT_HOST else args.host
    print(f"Serving on http://{display_host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
