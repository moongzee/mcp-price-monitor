import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # MCP 서버 실행 파일 경로
    server_params = StdioServerParameters(
        command="python",
        args=["src/price_monitor_mcp.py"],  # 실제 MCP 서버 파일 경로로 수정
    )
    # MCP 서버와 연결
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # monitor_price_workflow 툴 실행
            result = await session.call_tool("monitor_price_workflow", arguments={"product_code": "ULCK25151"})
            print("워크플로우 결과:", result)

if __name__ == "__main__":
    asyncio.run(main())