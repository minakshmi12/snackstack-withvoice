#build SnackStack, a voice-enabled multi-agent food delivery assistant powered by LangGraph. The system accepts user queries (text or voice), routes them through an orchestrator to specialist agents (Menu Agent and Order Agent), and returns a unified response.

This project covers core concepts in modern AI application development: multi-agent orchestration, RAG (Retrieval-Augmented Generation), structured LLM output, tool calling, human-in-the-loop interaction, and voice I/O.

A CLI-based assistant for a fictional food delivery platform called SnackStack. The system should:
Accept natural language queries via text input (and optionally voice)
Route queries to the correct specialist agent(s) using an LLM-powered orchestrator
Search a menu catalog using semantic search (RAG with ChromaDB)
Look up order status by Order ID, Tracking ID, or email
Ask the user for missing information when needed (Human-in-the-Loop)
Merge responses from multiple agents into a single friendly reply
Optionally support voice input (Whisper STT) and voice output (OpenAI TTS)
