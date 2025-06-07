from fastmcp import Client
import asyncio
from pprint import pprint

config = {
    "mcpServers": {
        "course": {"url": "http://127.0.0.1:8000/mcp", "transport": "streamable-http"},
        "calculator": {
            "command": "python",
            "args": ["./mcp_server.py"],
        },
    }
}

client = Client(config)


async def main():
    async with client:
        tools_list = await client.list_tools()
        print("\n[툴 리스트]:")
        pprint(tools_list)

        tool_call_result = await client.call_tool(
            name="course_check_available_seats",
            arguments={"course_name": "파이썬 데이터 분석 입문"},
        )
        print("\n[툴 호출 결과-1]:", tool_call_result)

        tool_call_result = await client.call_tool(
            name="calculator_add",
            arguments={"a": 10, "b": 20},
        )
        print("\n[툴 호출 결과-2]:", tool_call_result)


if __name__ == "__main__":
    asyncio.run(main())
