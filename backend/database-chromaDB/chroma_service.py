import chromadb
from dotenv import load_dotenv
from os import getenv

load_dotenv()

client = chromadb.HttpClient(port=int(getenv("CHROMADB_PORT")), host="localhost")

# To be developed