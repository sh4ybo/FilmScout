from flask import request
import jwt
from bson import ObjectId
from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.film_scout

secret_key = 'marley'

def valid_object_id(id):
    return ObjectId.is_valid(id)

def get_current_user():
    token = request.headers['x-access-token']
    data = jwt.decode(token, secret_key, algorithms='HS256')
    return data['user'], data['admin']