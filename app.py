from flask import Flask, request, jsonify, make_response
from pymongo import MongoClient
from bson import ObjectId
import datetime
import bcrypt
from functools import wraps
import jwt
import validators

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
            return make_response(jsonify({'message' : 'admin required'}), 403)
    return admin_required_wrapper

def valid_object_id(id):
    return ObjectId.is_valid(id)

def get_current_user():
    token = request.headers['x-access-token']
    data = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')
    return data['user'], data['admin']

#movies
@app.route("/api/v1.0/movies", methods=["GET"])
def show_all_movies():
    #pagination
    page_num, page_size = 1,10
    try:
        if request.args.get('pn'):
            page_num = int(request.args.get('pn'))
        if request.args.get('ps'):
            page_size = int(request.args.get('ps'))
    except ValueError:
        return make_response( jsonify( { 'ERROR' : 'Page size/number must be a number' } ), 400)

    if page_size < 1 or page_size > 100:
        return make_response(jsonify({'ERROR': 'Page size must be 1-100'}), 400)
    if page_num <1 :
        return make_response(jsonify({'ERROR': 'Page number must be at least 1'}), 400)

    page_start = page_size * (page_num - 1)

    #search by title and genre
    query = {}
    title = request.args.get('title', '').strip()
    genres = request.args.get('genres', '').strip()

    if title:
        query['title'] = {
            '$regex' : title,
            '$options' : 'i'
        }

    if genres:
        genre_list = [g.strip() for g in genres.split(',') if g.strip()]
        if not genre_list:
            return make_response(jsonify({'ERROR': 'Please enter valid genres'}), 400)

        query['genres'] = {
            '$all' : genre_list
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
    if not valid_object_id(id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)

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
        return make_response(jsonify({'ERROR':'Invalid Movie ID'}), 400)

@app.route("/api/v1.0/movies", methods=['POST'])
@jwt_required
@admin_required
def add_movie():
    title = request.form.get('title','').strip()
    genres = request.form.get('genres','').strip()

    if not title or not genres:
        return make_response(jsonify({'ERROR': 'Title and Genres required'}), 400)

    genre_list = [ genre.strip() for genre in genres.split(',') if genre.strip() ]

    if not genre_list:
        return make_response(jsonify({'ERROR': 'At least 1 genre is required'}), 400)

    if 'title' in request.form and 'genres' in request.form:
        new_movie = {
            "title": title,
            "genres": genre_list,
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
    if not valid_object_id(id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)

    title = request.form.get('title','').strip()
    genres = request.form.get('genres','').strip()

    if not title or not genres:
        return make_response(jsonify({'ERROR': 'Title and Genres required'}), 400)

    genre_list = [ genre.strip() for genre in genres.split(',') if genre.strip() ]

    if not genre_list:
        return make_response(jsonify({'ERROR': 'At least 1 genre is required'}), 400)

    result = movies.update_one( { '_id' : ObjectId(id) } , {
        "$set" : {
            "title" : title,
            "genres" : genre_list,
        }
    } )
    if result.matched_count == 1:
        edited_movie_link = "http://localhost:5000/api/v1.0/movies/" + id
        return make_response( jsonify({"url" : edited_movie_link} ), 200)
    else:
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 404)

@app.route("/api/v1.0/movies/<string:id>", methods=['DELETE'])
@jwt_required
@admin_required
def delete_business(id):
    if not valid_object_id(id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)

    result = movies.delete_one({'_id': ObjectId(id)})
    if result.deleted_count == 1:
        return make_response( jsonify( {}), 200)
    else:
        return make_response(jsonify({'ERROR':'Invalid Movie ID'}), 404)

#movie reviews
@app.route("/api/v1.0/movies/<string:id>/reviews", methods=['GET'])
def get_all_reviews(id):
    if not valid_object_id(id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)

    data_to_return = []
    movie = movies.find_one({'_id' : ObjectId(id)}, {'reviews':1 , '_id':0})
    if movie is not None:
        for review in movie.get('reviews', []):
            review['_id'] = str(review['_id'])
            data_to_return.append(review)
        return make_response( jsonify( data_to_return), 200)
    else:
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 404)

@app.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=['GET'])
def get_one_review(m_id, r_id):
    if not valid_object_id(m_id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)
    if not valid_object_id(r_id):
        return make_response(jsonify({'ERROR': 'Invalid Review ID'}), 400)

    movie = movies.find_one({'_id' : ObjectId(m_id)}, {"_id" : 1})
    if movie is None:
        return make_response(jsonify({ "ERROR" : "Invalid Movie ID"}), 404)

    movie = movies.find_one({
        "_id" : ObjectId(m_id),
        "reviews._id" : ObjectId(r_id)
    },
        {"_id" : 0, "reviews.$" : 1})
    if movie is None:
        return make_response(jsonify({ "ERROR" : "Invalid Review ID"}), 404)

    movie['reviews'][0]['_id'] = str(movie['reviews'][0]['_id'])
    return make_response(jsonify(movie['reviews'][0]), 200)

@app.route("/api/v1.0/movies/<string:id>/reviews", methods=['POST'])
@jwt_required
def add_review(id):
    if not valid_object_id(id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)

    username, admin = get_current_user()

    stars = request.form.get('stars','').strip()
    try:
        stars = int(stars)
    except ValueError:
        return make_response( jsonify( {'ERROR' : 'Rating must be a number' } ), 400 )

    if stars < 1 or stars >5:
        return make_response(jsonify({'ERROR': 'Rating must between 1 and 5'}), 400)
    if stars and 'comment' in request.form:
        new_review = {
            '_id' : ObjectId(),
            'username' : username,
            'stars' : str(stars),
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

@app.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=['PUT'])
@jwt_required
def edit_review(m_id, r_id):
    if not valid_object_id(m_id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)
    if not valid_object_id(r_id):
        return make_response(jsonify({'ERROR': 'Invalid Review ID'}), 400)

    username, admin = get_current_user()

    movie = movies.find_one({'_id': ObjectId(m_id)}, {"_id": 1})
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Movie ID"}), 404)

    movie = movies.find_one({
        "_id": ObjectId(m_id),
        "reviews._id": ObjectId(r_id)
    },
        {"_id": 0, "reviews.$": 1})
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Review ID"}), 404)

    review = movie['reviews'][0]
    if review['username'] != username and not admin:
        return make_response(jsonify({'ERROR' : 'you cannot edit this review'}), 403)

    stars = request.form.get('stars','').strip()

    if not stars or not 'comment' in request.form:
        return make_response(jsonify({'ERROR': 'Stars and comment required'}), 400)
    try:
        stars = int(stars)
    except ValueError:
        return make_response(jsonify({'ERROR': 'Rating must be a number'}), 400)

    if stars < 1 or stars > 5:
        return make_response(jsonify({'ERROR': 'Rating must between 1 and 5'}), 400)

    edited_review = {
        "reviews.$.stars": request.form['stars'],
        "reviews.$.comment": request.form['comment']
    }
    movies.update_one(
        {
            "_id": ObjectId(m_id),
            "reviews._id": ObjectId(r_id)},
        {"$set": edited_review}
    )
    edited_review_url = "http://localhost:5000/api/v1.0/movies/" + m_id \
                        + "/reviews/" + r_id
    return make_response(jsonify({"url": edited_review_url}), 200)

@app.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=['DELETE'])
@jwt_required
def delete_review(m_id, r_id):
    if not valid_object_id(m_id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)
    if not valid_object_id(r_id):
        return make_response(jsonify({'ERROR': 'Invalid Review ID'}), 400)

    username, admin = get_current_user()

    movie = movies.find_one({'_id': ObjectId(m_id)}, {"_id": 1})
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Movie ID"}), 404)

    movie = movies.find_one({
        "_id": ObjectId(m_id),
        "reviews._id": ObjectId(r_id)
    },
        {"_id": 0,
         "reviews.$": 1
         }
    )
    if movie is None:
        return make_response(jsonify({"Error": "Invalid Review ID"}), 404)

    review = movie['reviews'][0]
    if review['username'] != username and not admin:
        return make_response(jsonify({'ERROR' : 'You cannot delete this review'}), 403)

    movies.update_one( {
        "_id" : ObjectId(m_id)
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
    if not auth:
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
    name = request.form.get('name', '').strip()
    username = request.form.get('username','').strip()
    password =request.form.get('password','').strip()
    email = request.form.get('email', '').strip()

    if name and username and password and email:
        if len(username) < 3 or len(username) > 30:
            return make_response(jsonify({'message': 'Username must be between 3 and 30 characters'}), 400)

        if len(password) < 3 or len(password) > 30:
            return make_response(jsonify({'message': 'Password must be between 3 and 30 characters'}), 400)

        if not validators.email(email):
            return make_response(jsonify({'message': 'Must enter valid email'}), 400)

        if users.find_one({'username' : username }):
            return make_response(jsonify({'message' : 'username already in use'}), 409)

        if users.find_one({'email' : email }):
            return make_response(jsonify({'message': 'email already in use'}), 409)

        new_user = {
            "name": name,
            "username": username,
            "password": bcrypt.hashpw(bytes(password, 'UTF-8'), bcrypt.gensalt()),
            "email": email,
            "admin": False
        }
        users.insert_one(new_user)

        return make_response(jsonify({'message' : 'user created'}), 201)
    else:
        return make_response(jsonify({'ERROR' : 'missing form data'}), 400)



if __name__ == "__main__":
    app.run( debug = True )