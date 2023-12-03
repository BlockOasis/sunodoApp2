# from pydantic import BaseModel, Field
from typing import Dict, Optional

from .model import User


class UsersDatabase:
    def __init__(self):
        self.users: Dict[str, User] = {}

    def create_user(self, user_id: str) -> User:
        """
        Creates a new user and adds it to the database.
        """
        new_user = User(
            open_claims={},
            open_disputes={},
            total_disputes=0,
            won_disputes=0,
            total_claims=0,
            correct_claims=0,
        )
        self.users[user_id] = new_user
        return new_user

    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """
        Updates information for a specific user.
        """
        user = self.users.get(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            return user
        return None

    def get_user(self, user_id: str) -> Optional[User]:
        """
        Retrieves a user by their ID.
        """
        return self.users.get(user_id)

    def get_all_users(self) -> Dict[str, User]:
        """
        Retrieves all users in the database.
        """
        return self.users
    
    def won_claim(self, user_id, claimID) -> Optional[User]:
        user = self.users.get(user_id)
        user.total_claims += 1
        user.correct_claims += 1
        del user.open_claims[claimID]
        return user
    
    def lost_claim(self, user_id, claimID) -> Optional[User]:
        user = self.users.get(user_id)
        user.total_claims += 1
        del user.open_claims[claimID]


users_db = UsersDatabase()
