"""Verified identity boundary for the standalone API; no client-supplied UID."""
import asyncio
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request
from .config import Settings, get_settings

@dataclass(frozen=True)
class Principal:
    uid: str

async def get_principal(request: Request, settings: Settings = Depends(get_settings)) -> Principal:
    if settings.auth_mode == "local":
        host = request.client.host if request.client else ""
        allowed = {"127.0.0.1", "::1"}
        if settings.app_env == "test":
            allowed.add("testclient")
        if settings.app_env not in {"development", "test"} or host not in allowed:
            raise HTTPException(403, "Local mode requires a development loopback client")
        return Principal("local")
    if settings.auth_mode != "firebase":
        raise HTTPException(503, "Authentication is not configured")
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "A verified bearer token is required")
    try:
        import firebase_admin
        from firebase_admin import auth
        try:
            app = firebase_admin.get_app("diligence-auth")
        except ValueError:
            app = firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id}, name="diligence-auth")
        claims = await asyncio.to_thread(auth.verify_id_token, header[7:], app=app, check_revoked=True)
        uid = claims.get("uid") or claims.get("sub")
        if not uid:
            raise ValueError("Missing subject")
        return Principal(uid)
    except ImportError as exc:
        raise HTTPException(503, "Firebase authentication dependency unavailable") from exc
    except Exception as exc:
        raise HTTPException(401, "Invalid or expired bearer token") from exc
