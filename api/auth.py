"""API 鉴权。支持本地免鉴权、API Key。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings

_security = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


async def require_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
) -> None:
    """鉴权依赖。本地 IP 可免鉴权，否则需 API Key。"""
    settings = get_settings()
    client_ip = _get_client_ip(request)

    if settings.allow_local_no_auth and client_ip in ("127.0.0.1", "localhost", "::1"):
        return

    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.headers.get("X-API-Key")
    if not token:
        token = request.query_params.get("api_key")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证凭证，请提供 api_key 参数或 X-API-Key 请求头",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not (settings.api_key and token == settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )
