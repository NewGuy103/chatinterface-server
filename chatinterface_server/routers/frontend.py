import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..dependencies import login_required
from ..models.common import AppState, SessionInfo

router: APIRouter = APIRouter(prefix="/frontend", tags=['frontend'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.frontend")


@router.get('/', response_class=HTMLResponse)
async def root_path(
    req: Request,
    session: Annotated[SessionInfo | RedirectResponse, Depends(login_required)]
):
    state: AppState = req.state
    if isinstance(session, RedirectResponse):
        return session

    return state.templates.TemplateResponse(
        request=req, name='root_path.html'
    )


@router.get('/login', response_class=HTMLResponse)
async def login_path(req: Request, session: Annotated[SessionInfo | RedirectResponse, Depends(login_required)]):
    state: AppState = req.state
    if isinstance(session, SessionInfo):
        return RedirectResponse('/frontend/')

    return state.templates.TemplateResponse(
        request=req, name='login_path.html'
    )
