class ChatsRepositoryAdapter:
    """SessionPool-backed adapter for SpamStatusService repository access."""

    def __init__(self, session_pool):
        self._session_pool = session_pool

    def get_all_chats(self):
        from db.repositories import ChatsRepository
        with self._session_pool() as session:
            return ChatsRepository(session).get_all_chats()

    def add_user_to_chat(self, chat_id: int, member):
        from db.repositories import ChatsRepository
        with self._session_pool() as session:
            result = ChatsRepository(session).add_user_to_chat(chat_id, member)
            session.commit()
            return result

    def remove_user_from_chat(self, chat_id: int, user_id: int):
        from db.repositories import ChatsRepository
        with self._session_pool() as session:
            result = ChatsRepository(session).remove_user_from_chat(chat_id, user_id)
            session.commit()
            return result

    def get_user_id(self, username: str):
        from db.repositories import ChatsRepository
        with self._session_pool() as session:
            return ChatsRepository(session).get_user_id(username)

    def get_user_by_id(self, user_id: int):
        from db.repositories import ChatsRepository
        with self._session_pool() as session:
            return ChatsRepository(session).get_user_by_id(user_id)

    def save_user_type(self, user_id: int, user_type: int):
        from db.repositories import ChatsRepository
        with self._session_pool() as session:
            ChatsRepository(session).save_user_type(user_id, user_type)
            session.commit()
            return True
