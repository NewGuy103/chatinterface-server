from typing import Annotated
from pydantic import BaseModel, Field
from .common import UsernameField


class AddUser(BaseModel):
    username: UsernameField
    password: Annotated[str, Field(max_length=100, min_length=1)]
