from fastmcp import Client
import asyncio
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create a standard MCP configuration with HTTP server
config = {
    "mcpServers": {
        "local": {"command": "python", "args": ["my_assistant_server.py"]},
        "remote": {"url": "https://example.com/mcp"},
    }
}

logger.debug(f"Config: {config}")

# Create a client that connects to the local server
client = Client(config)


async def main():
    try:
        logger.info("Connecting to MCP server...")
        async with client:
            logger.info("Connected successfully!")

            # List available tools
            logger.info("Listing tools...")
            tool_list = await client.list_tools()
            logger.info(f"Available tools: {tool_list}")

            # Call the multiply tool
            logger.info("Calling multiply tool...")
            result = await client.call_tool("multiply", {"a": 5, "b": 3})
            logger.info(f"Multiply result: {result}")

            # Access resources
            logger.info("Reading config resource...")
            config = await client.read_resource("data://config")
            logger.info(f"Config: {config}")
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
