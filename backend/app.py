from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db
from models import ChatHistory  
from routes.chat_routes import chat_blueprint, chat_api
from flask_cors import CORS
from qdrant_client import QdrantClient
from routes.chat_routes import get_site_stats_from_qdrant


app = Flask(__name__)
CORS(app)  # 👈 Allow cross-origin requests


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(chat_blueprint, url_prefix="/chat")
app.register_blueprint(chat_api)


if __name__ == "__main__":
    print(get_site_stats_from_qdrant())
    with app.app_context():
        db.create_all()   # This will now properly create chat_history table
    app.run(debug=True)
