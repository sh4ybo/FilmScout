import datetime
import bcrypt
import jwt
import validators
from flask import Blueprint,request, make_response, jsonify
from decorators import jwt_required, admin_required
import globals


auth_bp = Blueprint("auth_bp", __name__)

blacklist = globals.db.blacklist
users = globals.db.users

@auth_bp.route("/api/v1.0/login", methods=["GET"])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({'message': 'authentication required'}), 401)

    user = users.find_one( { 'username' : auth.username } )
    if user is not None:
        if bcrypt.checkpw( bytes( auth.password, 'UTF-8'), user['password']):
            token = jwt.encode({
                'user':auth.username,
                'admin':user['admin'],
                'exp' : datetime.datetime.now( datetime.UTC ) + datetime.timedelta( minutes=30 )
            }, globals.secret_key, algorithm='HS256')
            return make_response(jsonify( { 'token' : token } ), 200 )
        else:
                return make_response( jsonify( {'message' : 'bad password' } ),401 )
    else:
            return make_response( jsonify( {'message' : 'bad username' } ), 401 )


@auth_bp.route("/api/v1.0/logout", methods=["GET"])
@jwt_required
def logout():
    token = request.headers['x-access-token']
    blacklist.insert_one({ 'token' : token})
    return make_response(jsonify({ 'message' : 'Logout successful'}), 200)

@auth_bp.route("/api/v1.0/register", methods=["POST"])
def register():
    name = request.form.get('name', '').strip()
    username = request.form.get('username','').strip()
    password =request.form.get('password','')
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
