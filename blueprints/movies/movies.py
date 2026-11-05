from flask import Blueprint,request, make_response, jsonify
from decorators import jwt_required, admin_required
from bson import ObjectId
import globals
from globals import valid_object_id

movies_bp = Blueprint("movies_bp", __name__)
movies =  globals.db.movies


@movies_bp.route("/api/v1.0/movies", methods=["GET"])
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
        return make_response(jsonify( { 'ERROR': 'Page size must be 1-100' } ), 400)
    if page_num <1 :
        return make_response(jsonify( { 'ERROR': 'Page number must be at least 1' } ), 400)

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
        genre_list = [genre.strip() for genre in genres.split(',') if genre.strip()]
        if not genre_list:
            return make_response(jsonify( { 'ERROR': 'Please enter valid genres' } ), 400)

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

@movies_bp.route("/api/v1.0/movies/<string:id>", methods=["GET"])
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
        return make_response(jsonify( { 'ERROR':'Invalid Movie ID' } ), 400)

@movies_bp.route("/api/v1.0/movies", methods=['POST'])
@jwt_required
@admin_required
def add_movie():
    title = request.form.get('title','').strip()
    genres = request.form.get('genres','').strip()

    if not title or not genres:
        return make_response(jsonify( { 'ERROR': 'Title and Genres required' } ), 400)

    genre_list = [ genre.strip() for genre in genres.split(',') if genre.strip() ]

    if not genre_list:
        return make_response(jsonify( { 'ERROR': 'At least 1 genre is required' } ), 400)

    if 'title' in request.form and 'genres' in request.form:
        new_movie = {
            "title": title,
            "genres": genre_list,
            "ratings": [],
            "reviews": []
        }
        new_movie_id = movies.insert_one( new_movie )
        new_movie_link = "http://localhost:5000/api/v1.0/movies/" + str( new_movie_id.inserted_id )
        return make_response(jsonify( { "url" : new_movie_link } ), 201)
    else:
        return make_response(jsonify( { 'ERROR': 'Missing form data' } ), 404)

@movies_bp.route("/api/v1.0/movies/<string:id>", methods=['PUT'])
@jwt_required
@admin_required
def update_movie(id):
    if not valid_object_id(id):
        return make_response(jsonify( { 'ERROR': 'Invalid Movie ID' } ), 400)

    title = request.form.get('title','').strip()
    genres = request.form.get('genres','').strip()

    if not title or not genres:
        return make_response(jsonify( { 'ERROR': 'Title and Genres required' } ), 400)

    genre_list = [ genre.strip() for genre in genres.split(',') if genre.strip() ]

    if not genre_list:
        return make_response(jsonify( { 'ERROR': 'At least 1 genre is required' } ), 400)

    result = movies.update_one( { '_id' : ObjectId(id) } , {
        "$set" : {
            "title" : title,
            "genres" : genre_list,
        }
    } )
    if result.matched_count == 1:
        edited_movie_link = "http://localhost:5000/api/v1.0/movies/" + id
        return make_response( jsonify( {"url" : edited_movie_link} ), 200)
    else:
        return make_response(jsonify( {'ERROR': 'Invalid Movie ID'} ), 400)

@movies_bp.route("/api/v1.0/movies/<string:id>", methods=['DELETE'])
@jwt_required
@admin_required
def delete_business(id):
    if not valid_object_id(id):
        return make_response(jsonify( { 'ERROR': 'Invalid Movie ID' } ), 400)

    result = movies.delete_one( { '_id': ObjectId(id) } )
    if result.deleted_count == 1:
        return make_response( jsonify( {}), 200)
    else:
        return make_response(jsonify( {'ERROR':'Invalid Movie ID'} ), 404)