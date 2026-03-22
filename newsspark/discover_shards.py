import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGO_URI")

client = MongoClient(uri)
topology = client.topology_description
print("Replica Set Name:", topology.replica_set_name)
print("Shard hosts:", [s.address for s in topology.server_descriptions().values()])
