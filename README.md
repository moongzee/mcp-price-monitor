# Price Monitor MCP 서버
[![smithery badge](https://smithery.ai/badge/@moongzee/mcp-price-monitor)](https://smithery.ai/server/@moongzee/mcp-price-monitor)

## 개요

이 프로젝트는 Model Context Protocol(MCP) 기반의 가격 모니터링 서버입니다. 상품 코드로 DB 기준가와 G마켓 실시간 가격을 비교하고, 가격 하락 시 슬랙으로 알림을 전송합니다.

- **MCP 표준**을 따르는 서버/툴/프롬프트 구조
- **크롤링, 가격비교, 알림** 전체 프로세스 자동화
- **슬랙 웹훅** 연동 지원

---

## 주요 기능

1. **DB 기준가 조회**: 상품코드로 DB에서 기준 가격을 조회
2. **G마켓 실시간 가격 크롤링**: Firecrawl API 활용
3. **가격 비교 및 할인율 계산**
4. **가격 하락 시 슬랙 알림 전송**
5. **전체 워크플로우 자동 실행 툴 제공**

---

## 폴더 구조

```
price_monitor_mcp/
├── src/
│   └── price_monitor_mcp.py   # MCP 서버 메인 코드
├── mcp_client.py              # MCP 클라이언트 코드
├── README.md                  
└── .env                       # 환경변수
```

---

## 실행 방법

### Installing via Smithery

To install Price Monitor Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@moongzee/mcp-price-monitor):

```bash
npx -y @smithery/cli install @moongzee/mcp-price-monitor --client claude
```

### 1. 가상환경 준비 및 패키지 설치

```bash
conda activate price_monitor_mcp
pip install -r requirements.txt
# 또는 필요한 경우
pip install mcp firecrawl requests python-dotenv psycopg2-binary pydantic
```

### 2. 환경 변수 설정

`.env` 파일에 아래와 같이 슬랙 웹훅 등 환경변수를 설정하세요.
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DB_HOST=...
DB_PORT=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
```

### 3. MCP 서버 실행

```bash
mcp run src/price_monitor_mcp.py
```

- 또는 dev툴로 실행: `mcp dev src/price_monitor_mcp.py`
- 또는 쉘 스크립트로 conda 환경 활성화 후 실행

---

## MCP 툴/프롬프트 목록

- `get_db_price(product_code)`: DB 기준가 조회
- `crawl_gmarket_price(product_code)`: G마켓 실시간 가격 크롤링
- `send_slack_alert(message)`: 슬랙 알림 전송
- `monitor_price_workflow(product_code)`: 전체 프로세스 자동 실행 (추천)
- `monitor_price(product_code)`: 프롬프트(LLM용)

---

## 전체 프로세스 자동 실행 (추천)

### 워크플로우 툴 호출 예시

#### MCP dev툴/클라이언트에서:
- `monitor_price_workflow` 툴을 선택, `product_code` 입력 후 실행
- 결과: DB 가격, 최저가, 가격차, 할인율, 슬랙 알림 여부 등 반환

#### 파이썬 클라이언트 예제
```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["src/price_monitor_mcp.py"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("monitor_price_workflow", arguments={"product_code": "ULCK25151"})
            print("워크플로우 결과:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 슬랙 알림 테스트
- 슬랙 웹훅이 올바르게 설정되어 있으면, 가격 하락 시 자동으로 알림이 전송됩니다.
- 메시지 포맷은 `send_slack_alert` 함수에서 자유롭게 수정 가능

---

## LLM(Claude, GPT 등) 연동
- Claude, GPT 등에서 MCP 서버 연결 기능이 공식 지원되면 자연어로 프롬프트/툴 실행 가능
- 현재는 MCP 클라이언트 코드로 결과를 받아 LLM에게 붙여넣어 요약/분석 요청

---

## 참고/문서
- [MCP Python SDK 공식 문서](https://github.com/modelcontextprotocol/python-sdk)
- Firecrawl, Slack API, DB 등은 각 환경에 맞게 설정 필요

---

## 문의/기여
- 궁금한 점, 버그, 확장 요청은 이슈로 남겨주세요! 
