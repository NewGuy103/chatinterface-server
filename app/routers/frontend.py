import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..dependencies import SessionOrRedirectDep
from ..models.common import AppState, SessionInfo

router: APIRouter = APIRouter(prefix="/frontend", tags=['frontend'])
logger: logging.Logger = logging.getLogger("chatinterface_server")


@router.get('/', response_class=HTMLResponse)
async def root_path(
    req: Request,
    session_or_redirect: SessionOrRedirectDep
):
    state: AppState = req.state
    if isinstance(session_or_redirect, RedirectResponse):
        return session_or_redirect

    return state.templates.TemplateResponse(
        request=req, name='root_path.html'
    )


@router.get('/login', response_class=HTMLResponse)
async def login_path(
    req: Request, 
    session_or_redirect: SessionOrRedirectDep
):
    state: AppState = req.state
    if isinstance(session_or_redirect, SessionInfo):
        return RedirectResponse('/frontend/')

    return state.templates.TemplateResponse(
        request=req, name='login_path.html'
    )
