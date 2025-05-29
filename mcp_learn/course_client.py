import asyncio
from fastmcp import Client

client = Client("course_server.py")


async def call_mcp():

    async with client:

        resources_list = await client.list_resources()
        print(resources_list)

        course_catalog = await client.read_resource("file://course_catalog.txt")
        print(course_catalog)

        tools_list = await client.list_tools()
        print(tools_list)
        result = await client.call_tool(
            "check_available_seats", {"course_name": "파이썬 데이터 분석 입문"}
        )
        print(result)

        # templates = await client.read_resource("gallery://pngfile")
        # print(templates)
        # # get the config
        # templates = await client.read_resource("data://config")
        # print(templates)

        # templates = await client.read_resource("users://john/profile")
        # print(templates)

        # prompts_list = await client.list_prompts()
        # print("Available prompts:", prompts_list)

        # # 2. 특정 프롬프트 호출하기
        # # 예시: analyze_data 프롬프트 호출
        # prompt_result = await client.get_prompt("analyze_data", {"data_points": "100"})
        # print("Prompt result:", prompt_result)


# asyncio.run(call_tool("Ford"))
asyncio.run(call_mcp("full"))
