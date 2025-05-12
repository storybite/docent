from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP()


@mcp.tool()
def add(
    a: int = Field(description="첫 번째 피연산자"),
    b: int = Field(description="두 번째 피연산자"),
) -> int:
    """
    a와 b를 더합니다.

    Args:
        a: 첫 번째 피연산자
        b: 두 번째 피연산자

    Returns:
        a와 b의 합
    """
    print(f"Adding {a} and {b}")
    return a + b


if __name__ == "__main__":
    mcp.run(transport="sse")
