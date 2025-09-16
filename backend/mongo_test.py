from pymongo import MongoClient
import certifi

client = MongoClient(
    "mongodb+srv://bairisriram:Gomathaa@cluster0.6xnoaxn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    tls=True,
    tlsCAFile=certifi.where()
)

print(client.list_database_names())  # should NOT raise error