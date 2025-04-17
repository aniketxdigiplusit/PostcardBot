from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db
from models import ChatHistory  
from routes.chat_routes import chat_blueprint
from flask_cors import CORS
from qdrant_client import QdrantClient



app = Flask(__name__)
CORS(app)  # 👈 Allow cross-origin requests

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(chat_blueprint, url_prefix="/chat")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # This will now properly create chat_history table
    app.run(debug=True)
