from flask import Blueprint,request, make_response, jsonify
from decorators import jwt_required, admin_required
import globals
from bson import ObjectId
from globals import valid_object_id, get_current_user

reviews_bp = Blueprint("reviews_bp", __name__)
movies =  globals.db.movies

@reviews_bp.route("/api/v1.0/movies/<string:id>/reviews", methods=['GET'])
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

@reviews_bp.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=['GET'])
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

@reviews_bp.route("/api/v1.0/movies/<string:id>/reviews", methods=['POST'])
@jwt_required
def add_review(id):
    if not valid_object_id(id):
        return make_response(jsonify({'ERROR': 'Invalid Movie ID'}), 400)

    username, admin = get_current_user()

    stars = request.form.get('stars','').strip()
    comment = request.form.get('comment','').strip()
    try:
        stars = int(stars)
    except ValueError:
        return make_response( jsonify( {'ERROR' : 'Rating must be a number' } ), 400 )

    if stars < 1 or stars >5:
        return make_response(jsonify({'ERROR': 'Rating must between 1 and 5'}), 400)
    if stars and comment:
        new_review = {
            '_id' : ObjectId(),
            'username' : username,
            'stars' : str(stars),
            'comment' : comment
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

@reviews_bp.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=['PUT'])
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
    comment = request.form.get('comment', '').strip()

    if not stars or not comment:
        return make_response(jsonify({'ERROR': 'Stars and comment required'}), 400)
    try:
        stars = int(stars)
    except ValueError:
        return make_response(jsonify({'ERROR': 'Rating must be a number'}), 400)

    if stars < 1 or stars > 5:
        return make_response(jsonify({'ERROR': 'Rating must between 1 and 5'}), 400)

    edited_review = {
        "reviews.$.stars": str(stars),
        "reviews.$.comment": comment
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

@reviews_bp.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=['DELETE'])
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
