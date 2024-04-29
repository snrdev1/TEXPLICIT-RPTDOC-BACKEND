import requests
from app import Config
from app.models.mongoClient import MongoClient
from app.utils.formatter import cursor_to_dict

def get_ip_data():
    ipstack_url = f"http://api.ipstack.com/check?access_key={Config.IPSTACK_API_KEY}"
    response = requests.get(ipstack_url)
    ip_data = response.json()
    
    return ip_data

def get_prices():
    m_db = MongoClient.connect()

    response = m_db[Config.MONGO_PRICING_MASTER_COLLECTION].find({})

    print("Response : ", response)

    return cursor_to_dict(response)
