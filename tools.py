from tavily import TavilyClient
from anthropic import Anthropic
import os

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
        "description": "역사적 사실 검색",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "사용자 질의에 답하기 위한 인터넷 검색 키워드",
                },
            },
        },
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


def search_relics(relics: dict, search_condition: dict):
    # 검색 조건에서 'Not Specified'가 아닌 항목만 필터링
    valid_conditions = {
        k: v for k, v in search_condition.items() if v != "Not Specified"
    }
    results = {}
    condition_keys = valid_conditions.keys()
    for artifact_id, artifact_data in relics.items():
        search_data = artifact_data["search"]
        if all(search_data.get(key) == valid_conditions[key] for key in condition_keys):
            results[artifact_id] = artifact_data

    return results


def get_tavily_response(query):
    response = tavily.search(
        query=query,
        include_domains=["ko.wikipedia.org", "encykorea.aks.ac.kr"],
        max_results=10,
        search_depth="advanced",
        include_answer="advanced",
    )
    return response["answer"], response


def check_search_(query, relics_index):
    matched_relics = []
    required_tool = get_required_tool(query, "search_relics")
    if required_tool:
        search_condition = map_to_korean(required_tool.input)
        matched_relics = search_relics(relics_index, search_condition)
        return matched_relics
    else:
        return None


def tool_call(query):
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1024,
        temperature=0,
        tools=tools,
        messages=[{"role": "user", "content": query}],
    )
    return response


def use_tools(query, relics_index):
    response = tool_call(query)
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
