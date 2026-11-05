from flask import Flask
from blueprints.movies.movies import movies_bp
from blueprints.reviews.reviews import reviews_bp
from blueprints.auth.auth import auth_bp

app = Flask(__name__)
app.register_blueprint(movies_bp)
app.register_blueprint(reviews_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run( debug = True )