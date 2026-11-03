from flask import Flask, request, jsonify, make_response
from pymongo import MongoClient
from bson import ObjectId
import datetime
import bcrypt
from functools import wraps
import jwt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'marley'
client = MongoClient("mongodb://127.0.0.1:27017")
db = client.film_scout
movies = db.movies
users = db.users
blacklist = db.blacklist

def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return make_response( jsonify( { 'message' : 'Token is missing' } ), 401 )
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms= 'HS256')
        except:
            return make_response( jsonify( { 'message' : 'Token is invalid' }), 401 )
        bl_token = blacklist.find_one( {'token' : token})
        if bl_token is not None:
            return make_response(jsonify({'message' : 'Token has been cancelled'}), 401)
        return func(*args, **kwargs)
    return jwt_required_wrapper

def admin_required(func):
    @wraps(func)
    def admin_required_wrapper(*args, **kwargs):
        token = request.headers['x-access-token']
        data = jwt.decode( token, app.config['SECRET_KEY'], algorithms='HS256')
        if data['admin']:
            return func(*args, **kwargs)
        else:
            return make_response(jsonify({'message' : 'admin required'}), 401)
    return admin_required_wrapper



#movies
@app.route("/api/v1.0/movies", methods=["GET"])
def show_all_movies():
    #pagination
    page_num, page_size = 1,10
    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))
    page_start = page_size * (page_num - 1)

    #search by title and genre
    query = {}

    if request.args.get('title'):
        query['title'] = {
            '$regex' : request.args.get('title'),
            '$options' : 'i'
        }

    if request.args.get('genres'):
        genres = request.args.get('genres').split(',')
        query['genres'] = {
            '$all' : genres
        }

    data_to_return = []
    for movie in movies.find(query).skip(page_start).limit(page_size):
        movie['_id'] = str(movie['_id'])
        total = 0
        count = 0

        for review in movie.get('reviews', []):
            review['_id'] = str(review['_id'])
            total += float(review['stars'])
            count += 1

        for rating in movie.get('ratings', []):
            rating['_id'] = str(rating['_id'])
            total += rating['rating']
            count += 1

        for tag in movie.get('tags', []):
            tag['_id'] = str(tag['_id'])

        if count > 0:
            movie['average_rating'] = round(total / count, 2)
        else:
            movie['average_rating'] = None

        data_to_return.append(movie)

    return make_response( jsonify( data_to_return ), 200 )

@app.route("/api/v1.0/movies/<string:id>", methods=["GET"])
@jwt_required
def show_one_movie(id):
    movie = movies.find_one( { '_id' : ObjectId(id) } )
    if movie is not None:
        movie['_id'] = str(movie['_id'])
        total = 0
        count = 0

        for review in movie.get('reviews', []):
            review['_id'] = str(review['_id'])
            total += float(review['stars'])
            count += 1

        for rating in movie.get('ratings', []):
            rating['_id'] = str(rating['_id'])
            total += rating['rating']
            count += 1

        for tag in movie.get('tags', []):
            tag['_id'] = str(tag['_id'])

        if count > 0:
            movie['average_rating'] = round(total / count, 2)
        else:
            movie['average_rating'] = None

        return make_response( jsonify(  movie ), 200 )
    else:
        return make_response(jsonify({'ERROR':'Invalid Movie ID'}), 404)

@app.route("/api/v1.0/movies", methods=['POST'])
@jwt_required
@admin_required
def add_movie():

    if 'title' in request.form and 'genres' in request.form:
        new_movie = {
            "title": request.form['title'],
            "genres": request.form['genres'].split(','),
            "ratings": [],
            "reviews": []
        }
        new_movie_id = movies.insert_one( new_movie )
        new_movie_link = "http://localhost:5000/api/v1.0/movies/" + str( new_movie_id.inserted_id)
        return make_response(jsonify( { "url" : new_movie_link } ), 201)
    else:
        return make_response(jsonify({'ERROR': 'Missing form data'}), 404)

@app.route("/api/v1.0/movies/<string:id>", methods=['PUT'])
@jwt_required
@admin_required
def update_movie(id):
    if 'title' in request.form and 'genres' in request.form:
        result = movies.update_one( { '_id' : ObjectId(id) } , {
            "$set" : {
                "title" : request.form['title'],
                "genres" : request.form['genres'].split(','),
            }
        } )
        if result.matched_count == 1:
            edited_movie_link = "http://localhost:5000/api/v1.0/movies/" + id
            return make_response( jsonify({"url" : edited_movie_link} ), 200)
        else:
            return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 404)
    else:
        return make_response(jsonify({'ERROR': 'Missing form data'}), 404)

@app.route("/api/v1.0/movies/<string:id>", methods=['DELETE'])
@jwt_required
@admin_required
def delete_business(id):
    result = movies.delete_one({'_id': ObjectId(id)})
    if result.deleted_count == 1:
        return make_response( jsonify( {}), 200)
    else:
        return make_response(jsonify({'ERROR':'Invalid Movie ID'}), 404)

#movie reviews
@app.route("/api/v1.0/movies/<string:id>/reviews", methods=['POST'])
@jwt_required
def add_review(id):
    if 'username' in request.form and 'stars' in request.form and 'comment' in request.form:
        new_review = {
            '_id' : ObjectId(),
            'username' : request.form['username'],
            'stars' : request.form['stars'],
            'comment' : request.form['comment']
            }
        result = movies.update_one({ '_id' : ObjectId( id ) }, {
                              "$push" : {'reviews' : new_review}
        } )
        if result.matched_count == 1:
            new_review_link = "http://localhost:5000/api/v1.0/movies/" + id + "/reviews/" + str(new_review['_id'])
            return make_response(jsonify({"url": new_review_link}), 201)

        else:
            return make_response(jsonify({'ERROR': 'Invalid movie ID'}), 404)

    else:
        return make_response(jsonify({'ERROR': 'Missing form data'}), 404)

@app.route("/api/v1.0/movies/<string:id>/reviews", methods=['GET'])
def get_all_reviews(id):
    data_to_return = []
    movie = movies.find_one({'_id' : ObjectId(id)}, {'reviews':1 , '_id':0})
    if movie is not None:
        for review in movie['reviews']:
            review['_id'] = str(review['_id'])
            data_to_return.append(review)
        return make_response( jsonify( data_to_return), 200)
    else:
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 404)

@app.route("/api/v1.0/movies/<string:b_id>/reviews/<string:r_id>", methods=['GET'])
def get_one_review(b_id, r_id):
    movie = movies.find_one({'_id' : ObjectId(b_id)}, {"_id" : 1})
    if movie is None:
        return make_response(jsonify({ "ERROR" : "Invalid Movie ID"}))

    movie = movies.find_one({"reviews._id" : ObjectId(r_id)}, {"_id" : 0, "reviews.$" : 1})
    if movie is None:
        return make_response(jsonify({ "ERROR" : "Invalid Review ID"}))

    movie['reviews'][0]['_id'] = str(movie['reviews'][0]['_id'])
    return make_response(jsonify(movie['reviews'][0]), 200)

@app.route("/api/v1.0/movies/<string:b_id>/reviews/<string:r_id>", methods=['PUT'])
@jwt_required
def edit_review(b_id, r_id):
    movie = movies.find_one({'_id': ObjectId(b_id)}, {"_id": 1})
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Business ID"}))

    movie = movies.find_one({"reviews._id": ObjectId(r_id)}, {"_id": 0, "reviews.$": 1})
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Review ID"}))

    edited_review = {
        "reviews.$.username": request.form['username'],
        "reviews.$.stars": request.form['stars'],
        "reviews.$.comment": request.form['comment']
    }
    movies.update_one(
        {"reviews._id": ObjectId(r_id)},
        {"$set": edited_review}
    )
    edited_review_url = "http://localhost:5000/api/v1.0/movies/" + b_id \
                        + "/reviews/" + r_id
    return make_response(jsonify({"url": edited_review_url}), 200)

@app.route("/api/v1.0/movies/<string:b_id>/reviews/<string:r_id>", methods=['DELETE'])
@jwt_required
@admin_required
def delete_review(b_id, r_id):
    movie = movies.find_one({'_id': ObjectId(b_id)}, {"_id": 1})
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Movie ID"}))

    movie = movies.find_one({"reviews._id": ObjectId(r_id)}, {"_id": 0, "reviews.$": 1})
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Review ID"}))

    movies.update_one( {
        "_id" : ObjectId(b_id)
    },{
        "$pull" : {
            "reviews" : {
                "_id" : ObjectId(r_id) }
        }
    })
    return make_response(jsonify( {} ), 200)

#auth
@app.route("/api/v1.0/login", methods=["GET"])
def login():
    auth = request.authorization
    if auth:
        user = users.find_one( { 'username' : auth.username } )
        if user is not None:
            if bcrypt.checkpw( bytes( auth.password, 'UTF-8'), user['password']):
                token = jwt.encode({
                    'user':auth.username,
                    'admin':user['admin'],
                    'exp' : datetime.datetime.now( datetime.UTC ) + datetime.timedelta( minutes=30 )
                }, app.config['SECRET_KEY'], algorithm='HS256')
                return make_response(jsonify( { 'token' : token } ), 200 )
            else:
                return make_response( jsonify( {'message' : 'bad password' } ),401 )
        else:
            return make_response( jsonify( {'message' : 'bad username' } ), 401 )
    return make_response(jsonify( {'message' : 'authentication required'} ), 401)

@app.route("/api/v1.0/logout", methods=["GET"])
@jwt_required
def logout():
    token = request.headers['x-access-token']
    blacklist.insert_one({ 'token' : token})
    return make_response(jsonify({ 'message' : 'Logout successful'}), 200)

@app.route("/api/v1.0/register", methods=["POST"])
def register():
    if 'name' in request.form and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        if users.find_one({'username' : request.form['username']}):
            return make_response(jsonify({'message' : 'username already in use'}), 409)
        if users.find_one({'email' : request.form['email']}):
            return make_response(jsonify({'message': 'email already in use'}), 409)

        new_user = {
            "name": request.form['name'],
            "username": request.form['username'],
            "password": bcrypt.hashpw(bytes(request.form['password'], 'UTF-8'), bcrypt.gensalt()),
            "email": request.form['email'],
            "admin": False
        }
        users.insert_one(new_user)

        return make_response(jsonify({'message' : 'user created'}), 201)
    else:
        return make_response(jsonify({'ERROR' : 'missing form data'}), 404)



if __name__ == "__main__":
    app.run( debug = True )