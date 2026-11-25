# 구현 계획: URL 단축기

## 목표와 원칙

- [SPEC.md](./SPEC.md)의 동작과 경계 사례를 기준으로 Python 3.11 이상 표준 라이브러리만 사용해 구현한다.
- `src/`의 각 기능을 분리하고 `tests/`에 표준 `unittest` 테스트를 둔다.
- 각 구현 단계에서 해당 테스트를 함께 작성하고 실행한다. 테스트를 마지막 단계까지 미루지 않는다.
- URL/code 매핑에는 직접 구현한 해시 테이블만 사용한다. 이 저장 구조에는 내장 `dict`, `set`, `hash()`를 사용하지 않는다. 단, JSON 파서가 반환한 객체에서 요청 필드를 읽는 것은 명세대로 허용한다.
- 코드는 URL의 해시값으로 만들지 않는다. 새 URL마다 증가하는 정수를 발급하고 `src/base62.py`의 인코더로 변환한다.

## 단계별 구현

### 1. base62 동작을 명세에 맞추고 테스트 보완

- 기존 `src/base62.py`의 `encode`와 `decode` 인터페이스를 유지한다.
- 명세가 인코딩의 음수 및 정수가 아닌 입력을 `ValueError`로 정하므로, 현재 비정수 입력의 예외 동작을 명세와 일치시킨다. `bool`도 정수로 취급하지 않는다.
- `tests/test_base62.py`를 갱신해 0, 61/62 경계, 큰 정수 왕복, 앞자리 0, 잘못된 입력과 예외 타입을 검증한다.
- 실행: `python -m unittest discover -s tests -p 'test_base62.py'`

### 2. 체이닝 해시 테이블 구현 및 단위 테스트

- `src/hash_table.py`에 문자열 키와 값을 저장하는 해시 테이블을 구현한다.
- 용량 8의 버킷 배열과 개별 체이닝을 사용하고, 명세의 호너 방식으로 인덱스를 계산한다. 빈 키는 인덱스 0으로 처리한다.
- `put`, `get`, `__contains__`, `__len__`를 제공한다. 기존 키의 갱신은 항목 수를 늘리지 않는다.
- 새 항목 삽입 후 적재율이 0.75를 초과하면 용량을 두 배로 늘리고 모든 항목을 재배치한다. 삭제 기능은 추가하지 않는다.
- `tests/test_hash_table.py`에서 충돌, 갱신, 없는 키, 빈 키, 7번째 삽입 직후의 리사이즈, 반복 리사이즈 후 조회를 검증한다.
- 실행: `python -m unittest discover -s tests -p 'test_hash_table.py'`

### 3. URL 단축 서비스와 검증 구현 및 테스트

- `src/shortener.py`에 `shorten(url)`과 `expand(code)`를 구현하고, URL→코드와 코드→URL 양방향 저장에 2단계의 사용자 정의 해시 테이블을 사용한다.
- 입력은 명세 순서대로 검증한다: 문자열 여부, 앞뒤 공백 제거 및 빈 값, 2048자 제한, ASCII 및 공백/제어 문자 금지, HTTP(S) scheme, 비어 있지 않은 hostname. 정규화는 앞뒤 공백 제거만 한다.
- 이미 등록한 URL은 기존 코드를 재사용한다. 새 URL은 0부터 증가하는 번호를 발급해 base62 인코딩하고, `(code, is_new)`를 반환한다.
- `expand`는 전달된 문자열 그대로 테이블에서 조회한다. 잘못된 형식 또는 미등록 코드는 `KeyError`로 처리해 `"00"`이 `"0"`과 같은 코드로 취급되지 않게 한다.
- `tests/test_shortener.py`에서 URL 검증 경계, 중복 URL, 코드 발급 순서와 고유성, 양방향 조회, 앞자리 0 코드를 검증한다.
- 실행: `python -m unittest discover -s tests -p 'test_shortener.py'`

### 4. HTTP 서버 구현 및 엔드포인트 테스트

- `src/server.py`에 표준 라이브러리 `HTTPServer`와 요청 핸들러를 구현한다. `make serve`가 기대하는 `--port` 인자를 지원하고 기본 포트는 8000, 바인딩 주소는 `127.0.0.1`로 한다.
- `GET /`는 입력창과 버튼이 있는 인라인 HTML을 반환하고, 브라우저의 `fetch`로 단축 요청을 보내 결과 또는 오류를 표시한다.
- `POST /api/shorten`은 본문을 읽기 전에 `Content-Length`를 확인해 8192바이트 초과를 413으로 응답한다. 빈 본문, 잘못된 JSON, 객체가 아닌 JSON, URL 누락/비문자열 및 URL 검증 실패는 400으로 처리한다. 성공 및 중복 응답은 각각 201 및 200 JSON으로 반환한다.
- `GET /<code>`는 쿼리 문자열을 제외한 코드로 조회해 성공 시 `302`와 `Location`을 반환하고, 미등록 코드는 404로 응답한다.
- `/api/shorten`의 POST 이외 메서드는 405, 그 외 경로의 미지원 요청과 POST는 명세대로 404로 처리한다. JSON 응답에는 항상 지정된 UTF-8 콘텐츠 타입을 사용한다.
- `tests/test_server.py`에서 실제 HTTP 요청을 사용해 정상/중복 생성, 리다이렉트 헤더, HTML, 오류 상태 코드와 요청 본문 경계를 검증한다. 테스트 서버는 임시 포트를 사용해 충돌을 피한다.
- 실행: `python -m unittest discover -s tests -p 'test_server.py'`

### 5. 통합 확인

- 전체 테스트를 실행해 모든 단계의 동작을 확인한다: `python -m unittest` 및 저장소 명령 `make test`.
- `make serve`가 실행되는지 확인하고, 브라우저 흐름에 해당하는 생성 요청과 단축 코드 리다이렉트를 점검한다.
- 명세와 구현을 대조해 상태 코드, 응답 형식, URL 정규화, 메모리 저장 범위 및 허용된 자료구조 사용을 최종 확인한다.

## 예상 파일

- 수정: `src/base62.py`, `tests/test_base62.py`
- 추가: `src/hash_table.py`, `src/shortener.py`, `src/server.py`
- 추가: `tests/test_hash_table.py`, `tests/test_shortener.py`, `tests/test_server.py`
