from flask import Flask
from routes.chat_routes import chat_blueprint

app = Flask(__name__)

# Register the blueprint with a prefix `/chat`
app.register_blueprint(chat_blueprint, url_prefix='/chat')

if __name__ == '__main__':
    app.run(debug=True)
