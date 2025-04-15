from tavily import TavilyClient
from anthropic import Anthropic
import os
from prompt_templates import history_based_prompt

client = Anthropic()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

tools = [
    {
        "name": "search_relics",
        "description": "박물관 전시물 검색",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {  # 시대
                    "type": "string",
                    "enum": [
                        "조선",
                        "고려",
                        "통일신라",
                        "신라",
                        "일제강점",
                        "삼국",
                        "백제",
                        "Not Specified",
                    ],
                },
                "designation": {  # 지정문화유산
                    "type": "string",
                    "enum": ["국보", "보물", "Not Specified"],
                },
                "architecture": {  # 건축
                    "type": "boolean",
                    "description": "건축 문화재 여부",
                },
                "sculpture": {  # 조각
                    "type": "boolean",
                    "description": "조각 문화재 여부",
                },
                "craft": {"type": "boolean", "description": "공예 문화재 여부"},  # 공예
                "painting": {  # 회화
                    "type": "boolean",
                    "description": "회화 문화재 여부",
                },
                "calligraphy": {  # 서예
                    "type": "boolean",
                    "description": "서예 문화재 여부",
                },
                "accessories": {  # 장신구
                    "type": "boolean",
                    "description": "장신구 문화재 여부",
                },
                "clothing": {  # 복식
                    "type": "boolean",
                    "description": "복식 문화재 여부",
                },
                "science": {  # 과학기술
                    "type": "boolean",
                    "description": "과학기술 관련 문화재 여부",
                },
                "buddhism": {  # 불교
                    "type": "boolean",
                    "description": "불교 관련 문화재 여부",
                },
            },
            "required": [
                "period",
                "designation",
                "architecture",
                "sculpture",
                "craft",
                "painting",
                "calligraphy",
                "accessories",
                "clothing",
                "science",
                "buddhism",
            ],
        },
    },
    {
        "name": "search_history_facts",
        "description": "역사적 사실에 대한 사용자의 질문에 답히기 위해 사용",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "사용자 질의에 답하기 위한 인터넷 검색 키워드",
                },
            },
        },
        # "cache_control": {"type": "ephemeral"},
    },
]


def get_required_tool(query, tool_name):
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1024,
        temperature=0,
        tools=tools,
        messages=[{"role": "user", "content": query}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block
    return None


def map_to_korean(result):
    return {
        "국적": "한국",  # 기본값으로 한국 설정
        "시대": result["period"],
        "지정문화유산": result["designation"],
        "건축": result["architecture"],
        "조각": result["sculpture"],
        "공예": result["craft"],
        "회화": result["painting"],
        "서예": result["calligraphy"],
        "장신구": result["accessories"],
        "복식": result["clothing"],
        "과학기술": result["science"],
        "불교": result["buddhism"],
    }


def search_relics(tool_input, relics: dict):

    search_condition = map_to_korean(tool_input)

    # 검색 조건에서 'Not Specified'가 아닌 항목만 필터링
    valid_conditions = {
        k: v for k, v in search_condition.items() if v != "Not Specified"
    }
    results = {}
    condition_keys = valid_conditions.keys()
    for artifact_id, artifact_data in relics.items():
        search_data = artifact_data["search"]
        # 모든 조건을 확인하되, 불리언 필드(건축~불교)는 하나라도 True면 통과
        match = True
        for key in condition_keys:
            # 문자열 필드 (국적, 시대, 지정문화유산)는 정확히 일치해야 함
            if key in ["국적", "시대", "지정문화유산"]:
                if search_data.get(key) != valid_conditions[key]:
                    match = False
                    break
            # 불리언 필드 (건축, 조각, 공예, 회화, 서예, 장신구, 복식, 과학기술, 불교)
            else:
                # 검색 조건은 True인 필드인데 데이터에 필드가 False면 불일치
                if valid_conditions[key] is True and search_data.get(key) is False:
                    match = False
                    break

        if match:
            results[artifact_id] = artifact_data

    message = (
        f"요청하신 전시물이 {len(results)}점 검색되었습니다. [다음] 버튼을 클릭해주세요."
        if len(results) > 0
        else "요청하신 전시물의 검색 결과가 없습니다."
    )

    return results, message


def get_tavily_response(query):
    tavily_response = tavily.search(
        query=query,
        include_domains=["ko.wikipedia.org", "encykorea.aks.ac.kr"],
        max_results=10,
        search_depth="advanced",
        include_answer="advanced",
    )
    return None, history_based_prompt.format(history_facts=tavily_response["answer"])


# def check_search_(query, relics_index):
#     matched_relics = []
#     required_tool = get_required_tool(query, "search_relics")
#     if required_tool:
#         matched_relics = search_relics(required_tool.input, relics_index)
#         return matched_relics
#     else:
#         return None


def tool_call(messages: list):
    response = client.messages.create(
        # model="claude-3-7-sonnet-20250219",
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        temperature=0,
        tools=tools,
        messages=messages,
    )
    print("tool_call cache:", response.usage.model_dump_json())
    return response


def use_tools(messages: list, database):
    response = tool_call(messages)
    if len(response.content) < 2:
        return None, None
    tool = response.content[1]

    result, message = None, None
    if tool.name == "search_relics":
        result, message = search_relics(tool.input, database)
    elif tool.name == "search_history_facts":
        result, message = get_tavily_response(tool.input["query"])
    else:
        raise ValueError("Invalid tool name")

    return result, message


def tool_call2(query, relics_index):
    response = client.messages.create(
        # model="claude-3-7-sonnet-20250219",
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        temperature=0,
        tools=tools,
        messages=[{"role": "user", "content": query}],
    )
    print("tool_call cache:", response.usage.model_dump_json())

    results = {}
    for block in response.content:
        if block.type == "tool_use":
            if block.name == "search_relics":
                search_condition = map_to_korean(block.input)
                matched_relics = search_relics(relics_index, search_condition)
                results[block.name] = matched_relics
            elif block.name == "search_history_facts":
                results[block.name], _ = get_tavily_response(block.input["query"])
    return results


def use_tools2(messages, user_input, relics_index):
    query = ""
    response = tool_call(query)
    results = {}
    for block in response.content:
        if block.type == "tool_use":
            if block.name == "search_relics":
                search_condition = ""
                matched_relics = search_relics(relics_index, search_condition)
                results[block.name] = matched_relics
            elif block.name == "search_history_facts":
                results[block.name], _ = get_tavily_response(block.input["query"])
    return results
