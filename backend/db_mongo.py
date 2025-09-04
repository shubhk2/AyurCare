import os
import re
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import Dict

# Load environment variables from .env file
load_dotenv()

# --- MongoDB Configuration ---
# Use environment variables or fallback to defaults
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("AYUSHMITRA")
COLLECTION_NAME = os.getenv("INGREDIENTS")

client = None
db = None
collection = None

def query():
    pipeline = [
        {
            # Add a field for the size of each dosha array.
            # Use $ifNull to handle cases where a dosha is not listed.
            '$addFields': {
                'vata_count': {'$size': {'$ifNull': ['$dosha_info.Vata', []]}},
                'pitta_count': {'$size': {'$ifNull': ['$dosha_info.Pitta', []]}},
                'kapha_count': {'$size': {'$ifNull': ['$dosha_info.Kapha', []]}}
            }
        },
        {
            # Match documents where any of the counts are greater than 1.
            '$match': {
                '$or': [
                    {'vata_count': {'$gt': 1}},
                    {'pitta_count': {'$gt': 1}},
                    {'kapha_count': {'$gt': 1}}
                ]
            }
        },
        {
            # Project the fields you want to see in the output.
            '$project': {
                'name': 1,
                'category': 1,
                'dosha_info': 1,
                '_id': 0
            }
        }
    ]
    if collection is not None:
    # Execute the aggregation
        results = collection.aggregate(pipeline)
        for doc in results:
            print(doc)
def get_database():
    """Establishes MongoDB connection and returns the collection object."""
    global client, db, collection
    if client is None:
        try:
            client = MongoClient(MONGO_URI)
            db = client[DB_NAME]
            # Test connection
            client.server_info()
            print(f"Successfully connected to MongoDB database '{DB_NAME}' and collection '{COLLECTION_NAME}'.")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            return None
    return db





if __name__ == "__main__":
    # scrape_and_save_data('../food_html.txt')
    get_database()
    query()