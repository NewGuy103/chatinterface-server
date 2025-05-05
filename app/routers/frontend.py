import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..dependencies import AuthOrRedirectDep
from ..models.common import AppState, UserInfo

router: APIRouter = APIRouter(prefix="/frontend", tags=['frontend'])
logger: logging.Logger = logging.getLogger("chatinterface_server")


@router.get('/', response_class=HTMLResponse)
async def root_path(
    req: Request,
    user_or_redirect: AuthOrRedirectDep
):
    state: AppState = req.state
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect

    return state.templates.TemplateResponse(
        request=req, name='root_path.html'
    )


@router.get('/login', response_class=HTMLResponse)
async def login_path(
    req: Request, 
    user_or_redirect: AuthOrRedirectDep
):
    state: AppState = req.state
    if isinstance(user_or_redirect, UserInfo):
        return RedirectResponse('/frontend/')

    return state.templates.TemplateResponse(
        request=req, name='login_path.html'
    )
