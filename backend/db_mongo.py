import os
import re
from pymongo import MongoClient
from bs4 import BeautifulSoup
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
            collection = db[COLLECTION_NAME]
            # Test connection
            client.server_info()
            print(f"Successfully connected to MongoDB database '{DB_NAME}' and collection '{COLLECTION_NAME}'.")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            return None
    return collection


def clean_ingredient_name(text: str) -> str:
    """Removes notes in parentheses and asterisks to get a clean name."""
    # Remove content in parentheses and asterisks
    name = re.sub(r'\(.*\)', '', text).replace('*', '').strip()
    # Basic singularization for common plurals
    if name.lower().endswith('es'):
        if len(name) > 3 and name.lower()[-3] not in 'aeiou':
            name = name[:-2]
    elif name.lower().endswith('s'):
        if len(name) > 2 and name.lower()[-2] not in 's':
            name = name[:-1]
    return name.title()


def extract_notes(text: str) -> str:
    """Extracts notes from an ingredient string, including conditions and moderation."""
    notes = []
    # Find content in parentheses
    match = re.search(r'\((.*?)\)', text)
    if match:
        notes.append(match.group(1))

    # Check for moderation asterisks
    if '**' in text:
        notes.append("okay rarely")
    elif '*' in text:
        notes.append("okay in moderation")

    return ", ".join(notes) if notes else None


def scrape_and_save_data(file_path: str):
    """
    Scrapes the food guideline data from the HTML file, processes it,
    and saves it to the MongoDB collection.
    """
    db_collection = get_database()
    if db_collection is None:
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')

    # This dictionary will temporarily hold the structured data
    # Key: ingredient name, Value: {category, dosha_info}
    all_foods: Dict[str, Dict] = {}

    # Find all food category sections
    food_sections = soup.find_all('div', class_='row')

    for section in food_sections:
        category_h2 = section.find('h2', class_='center')
        if not category_h2:
            continue

        category_name = category_h2.get_text(strip=True)
        table_content = section.find('div', class_='table-content')
        if not table_content:
            continue

        dosha_columns = table_content.find_all('div', class_='column large-4', recursive=False)

        for dosha_col in dosha_columns:
            print(dosha_col)
            dosha_name = dosha_col.find('h3').get_text(strip=True)

            # Column for items to 'Avoid'
            avoid_col = dosha_col.find('h4', string=re.compile('Avoid')).parent
            favor_col = dosha_col.find('h4', string=re.compile('Favor')).parent
            if avoid_col.find('h4'):
                avoid_col.find('h4').decompose()
            if favor_col.find('h4'):
                favor_col.find('h4').decompose()

            # Use get_text() with a separator to correctly handle the items
            avoid_items = [item.strip() for item in avoid_col.get_text(separator='<br>').split('<br>') if item.strip()]
            favor_items = [item.strip() for item in favor_col.get_text(separator='<br>').split('<br>') if item.strip()]


            # Process items to add to our main dictionary
            for status, item_list in [("Avoid", avoid_items), ("Favor", favor_items)]:
                for item in item_list:
                    # Skip any leftover header tags that might be in the list
                    if '<' in item and '>' in item:
                        continue

                    ingredient_name = clean_ingredient_name(item)
                    notes = extract_notes(item)

                    if not ingredient_name:
                        continue

                    # Initialize the ingredient if it's the first time we see it
                    if ingredient_name not in all_foods:
                        all_foods[ingredient_name] = {
                            "category": category_name,
                            "dosha_info": {}
                        }

                    # Add dosha information for the ingredient
                    status_info = {"status": status}
                    if notes:
                        status_info["notes"] = notes

                    if dosha_name not in all_foods[ingredient_name]["dosha_info"]:
                        all_foods[ingredient_name]["dosha_info"][dosha_name] = []

                    all_foods[ingredient_name]["dosha_info"][dosha_name].append(status_info)

    # --- Prepare documents for MongoDB ---
    mongo_documents = []
    for name, data in all_foods.items():
        doc = {
            "name": name,
            "category": data["category"],
            "dosha_info": data["dosha_info"]
        }
        mongo_documents.append(doc)

    # --- Insert into MongoDB ---
    if not mongo_documents:
        print("No data was scraped. Nothing to insert.")
        return

    try:
        # Clear the collection before inserting new data to prevent duplicates
        print(f"Deleting existing documents from '{COLLECTION_NAME}'...")
        delete_result = db_collection.delete_many({})
        print(f"Deleted {delete_result.deleted_count} documents.")

        # Insert the new documents
        print(f"Inserting {len(mongo_documents)} new documents...")
        db_collection.insert_many(mongo_documents)
        print("Data successfully scraped and saved to MongoDB!")
    except Exception as e:
        print(f"An error occurred during MongoDB operation: {e}")


if __name__ == "__main__":
    # scrape_and_save_data('../food_html.txt')
    get_database()
    query()