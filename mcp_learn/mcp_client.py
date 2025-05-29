import asyncio
from fastmcp import Client
from pathlib import Path


client = Client(Path(__file__).resolve().parent / "mcp_server1.py")


async def call_tool(name: str):
    async with client:
        # result = await client.call_tool("greet", {"name": name})
        result = await client.call_tool("fetch_weather", {"city": name})
        print(result)


# asyncio.run(call_tool("Ford"))
asyncio.run(call_tool("London"))
