import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAI, OpenAIEmbeddings
from src.logger import setup_logger
import sys

logger = setup_logger("config")
# Load environment variables from the .env file

load_dotenv()

# Get the OpenAI API key from the environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
    
  
    logger.error("OPENAI_API_KEY is missing. Copy .env.example → .env and add your key.")
    sys.exit(1)

# Configuration for OpenAI API key loaded successfully
logger.info("OpenAI API key loaded successfully.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
llm=ChatOpenAI(model="gpt-4o",  temperature=0.2)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

logger.info("OpenAI client, LLM, and embeddings initialized successfully with the provided API key, model gpt-4o, and embedding model text-embedding-3-small.")
  