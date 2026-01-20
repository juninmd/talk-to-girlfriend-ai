from backend.services.learning import learning_service


async def learn_from_chat(chat_id: int, limit: int = 100) -> str:
    """
    Ingests historical messages from a chat to learn facts and context.
    Use this when you start interacting with a new user or chat to get up to speed.
    """
    count = await learning_service.ingest_history(chat_id, limit)
    return f"Successfully ingested {count} messages from chat {chat_id} and triggered learning."
