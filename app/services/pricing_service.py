import requests

from app import Config
from app.models.mongoClient import MongoClient
from app.utils.formatter import cursor_to_dict


def get_ip_data():
    """
    The function `get_ip_data` makes a GET request to a specified URL and returns the JSON response
    containing IP data.

    Returns:
      The function `get_ip_data` is returning the IP data obtained from the IPStack API in JSON format.
    """
    ipstack_url = Config.IPSTACK_URL
    response = requests.get(ipstack_url)
    ip_data = response.json()

    return ip_data


def get_prices():
    """
    The function `get_prices` retrieves pricing information from multiple MongoDB collections and
    organizes the data by category.

    Returns:
      The `get_prices` function returns the result of aggregating data from multiple MongoDB collections
    based on the defined pipeline. The function executes the pipeline on the first collection in the
    `collection_names` list and returns the result as a dictionary.
    """
    m_db = MongoClient.connect()
    collection_names = [
        Config.MONGO_REPORT_PRICING_COLLECTION,
        Config.MONGO_DOCUMENT_PRICING_COLLECTION,
        Config.MONGO_CHAT_PRICING_COLLECTION
    ]

    # Get the collections
    collections = [m_db[coll_name] for coll_name in collection_names]

    # Define the pipeline
    pipeline = [
        {
            '$addFields': {
                'category': collection_names[0]
            }
        },
        {
            '$unionWith': {
                'coll': collection_names[1],
                'pipeline': [{'$addFields': {'category': collection_names[1]}}]
            }},
        {
            '$unionWith': {
                'coll': collection_names[2],
                'pipeline': [{'$addFields': {'category': collection_names[2]}}]
            }},
        {
            '$group': {
                '_id': '$category',
                'documents': {'$push': '$$ROOT'}
            }
        },
        {
            '$replaceRoot': {
                'newRoot': {
                    'category': '$_id',
                    'documents': '$documents'
                }
            }
        }
    ]

    # Execute the pipeline on the first collection and return the cursor
    result_cursor = collections[0].aggregate(pipeline)
    return cursor_to_dict(result_cursor)


def get_country_prices(country_name: str, pricing_plans):
    currency_code = "INR" if country_name.upper() == "INDIA" else "USD"
    country_prices = []

    for current_plan in pricing_plans:
        category = ' '.join(word.capitalize() for word in current_plan.get("category").split('_'))
        plans = []

        for price_info in current_plan.get("documents", []):

            report_price = next((p.get("value") for p in price_info.get("pricing", []) if p.get("currency_code") == currency_code), None)

            if report_price is not None:
                if category == "Document Pricing":
                    plans.append({"amount": price_info.get("amount", {}), "price": report_price})
                else:
                    plans.append({"count": price_info.get("count", 0), "price": report_price})

        if plans:  # Only add plans if there are valid prices
            country_prices.append({"category": category, "currency_code": currency_code, "plans": plans})

    return country_prices
