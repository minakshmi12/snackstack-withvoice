"""
rag.py
------
Retrieval-Augmented Generation (RAG) tools for SnackStack Multi-Agent System.

This module provides functions and classes to facilitate RAG operations,
allowing agents to retrieve relevant information from the knowledge base
and generate responses based on the retrieved context.

The vector store is used to index and retrieve relevant documents efficiently 
 based on semantic similarity for menu items.
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from src.config import embeddings
from src.data.menu import MENU_CATALOG
from src.logger import setup_logger
logger = setup_logger("rag")

def _build_documents() -> list[Document]:
    """Build a list of Document objects from the MENU_CATALOG."""
    documents = []
    for item in MENU_CATALOG:
        content = f"{item['name']} - {item['description']}"
        metadata = {
            "id": item["id"],
            "name": item["name"],
            "category": item["category"],
            "cuisine": item["cuisine"],
            "price": item["price"],
            "rating": item["rating"],
            "dietary_tags": item["dietary_tags"],
            "availability": item["availability"],
        }
        documents.append(Document(page_content=content, metadata=metadata))
    return documents

def build_vector_store() -> Chroma:
    """Build and return a Chroma vector store from the MENU_CATALOG documents."""
    documents = _build_documents()
    vector_store = Chroma.from_documents(documents=documents, embedding=embeddings, collection_name="snackstack_menu",)
    logger.info("Vector store built successfully with %d documents.", len(documents))
    return vector_store

#---Module-level vector store initialization-so every agent can access it efficiently---
menu_vector_store = build_vector_store()

def get_menu_vector_store(query: str):
    """Return the module-level menu vector store for the given query."""
    logger.info("Retrieving menu vector store for query: %s", query)
    try:
        docs = menu_vector_store.similarity_search(query, k=3)
        if not docs:
            return "No menu items found matching your query."
        results = "Found the following menu items:\n\n"
        for i, doc in enumerate(docs, 1):
            results += f"Menu Item {i}:\n{doc.page_content}\n\n"
        return results
    except Exception as exc:
        logger.exception("Catalog search failed")
        return f"Error searching catalog: {exc}"
    