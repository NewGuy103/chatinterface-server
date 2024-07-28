import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Query

from ..models import Model_SessionInfo, Model_AppState
from ..dependencies import get_session_info

router = APIRouter(prefix="/chat", tags=['chats'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.ws")


@router.get("/recipients")
async def get_previous_chats(
    session: Annotated[Model_SessionInfo, Depends(get_session_info)],
    req: Request
) -> set[str]:
    state: Model_AppState = req.state
    recipients: set[str] = await state.db.messages.get_previous_chats(session.username)
    return recipients


@router.get("/messages")
async def get_previous_messages(
    req: Request,
    recipient: Annotated[str, Query(description="Recipient username", max_length=20, strict=True)],

    amount: int = Query(100, description="Amount of messages to fetch (fetches latest messages)"),
    session: Annotated[Model_SessionInfo, Depends(get_session_info)] = None
) -> list[tuple[str, bytes, str]]:
    state: Model_AppState = req.state
    result: list[tuple[str, bytes, str]] | str = await state.db.messages.get_messages(
        session.username, recipient, amount
    )
    match result:
        case list():
            pass
        case "NO_RECIPIENT":
            raise HTTPException(status_code=404, detail="User not found")
        case _:
            logger.error("Unexpected data while fetching messages: %s", result)
            raise HTTPException(status_code=500, detail="Server error")

    return result
