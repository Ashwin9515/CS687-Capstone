from pymongo import MongoClient, errors
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Get the Mongo URI from .env
mongo_uri = os.getenv("MONGO_URI")

if not mongo_uri:
    print("❌ Error: MONGO_URI not found in environment.")
    exit(1)

try:
    # Initialize client
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)  # 5 second timeout
    # Force connection on a request as the connect=True parameter of MongoClient seems useless here
    print("✅ Connected to MongoDB!")
    print("📦 Databases:", client.list_database_names())

except errors.ServerSelectionTimeoutError as err:
    print("❌ Server Selection Timeout Error:", err)

except errors.OperationFailure as err:
    print("❌ Authentication or Operation Error:", err)

except Exception as e:
    print("❌ Unexpected Error:", e)