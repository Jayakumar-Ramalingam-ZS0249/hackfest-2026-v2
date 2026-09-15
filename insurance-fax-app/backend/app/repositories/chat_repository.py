"""In-memory chat conversation store, keyed by claim id."""


class ChatRepository:
    def __init__(self):
        self._conversations: dict[str, list[dict]] = {}

    def add_message(self, claim_id: str, message: dict) -> None:
        self._conversations.setdefault(claim_id, []).append(message)

    def get_history(self, claim_id: str) -> list[dict]:
        return self._conversations.get(claim_id, [])

    def clear(self, claim_id: str) -> None:
        self._conversations[claim_id] = []


chat_repository = ChatRepository()
