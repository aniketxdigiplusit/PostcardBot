from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ChatSession(db.Model):
    id = db.Column(db.String, primary_key=True)
    state = db.Column(db.JSON, nullable=False)

    def __init__(self, id, state):
        self.id = id
        self.state = state
