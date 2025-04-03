from models import ChatHistory, db
import logging

logger = logging.getLogger(__name__)

def save_message(thread_id: str, user_message: str, bot_response: str):
    """Save a user-bot exchange into the database"""
    try:
        message = ChatHistory(
            thread_id=thread_id,
            user_message=user_message,
            bot_response=bot_response
        )
        db.session.add(message)
        db.session.commit()
        logger.info(f"Saved message for thread {thread_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving message: {e}")

def get_chat_messages(thread_id: str, limit: int = 10) -> list:
    """Retrieve last N chat messages"""
    try:
        messages = ChatHistory.query.filter_by(thread_id=thread_id) \
                                    .order_by(ChatHistory.timestamp.desc()) \
                                    .limit(limit).all()

        history = []
        for msg in messages:
            history.append({"text": msg.user_message, "sender": "user"})
            history.append({"text": msg.bot_response, "sender": "bot"})
        return history
    except Exception as e:
        logger.error(f"Error retrieving chat messages: {e}")
        return []

def get_chat_history(thread_id: str, limit: int = 10) -> str:
    """Get chat history formatted as string for LLM"""
    try:
        messages = ChatHistory.query.filter_by(thread_id=thread_id) \
                                    .order_by(ChatHistory.timestamp.asc()) \
                                    .limit(limit).all()
        history = ""
        for msg in messages:
            history += f"User: {msg.user_message}\nBot: {msg.bot_response}\n\n"
        return history.strip()
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return ""
