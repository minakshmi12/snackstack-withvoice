from langchain_core.tools import tool
from src.logger import setup_logger
from src.tools.rag import get_menu_vector_store

logger = setup_logger("menu_tools")

@tool
def search_menu_catalog(query: str) -> list:
    """Search the menu catalog for items matching a natural-language query."""
    logger.info("Searching menu catalog for query: %s", query)
    result = get_menu_vector_store(query)
    return result

if __name__ == "__main__":
    # Quick manual smoke test
    print(search_menu_catalog.invoke({"query": "something creamy and non-vegetarian", "k": 3}))