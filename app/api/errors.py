"""JSON exception handlers and invalid-request quarantine."""
import json, logging
from typing import Any
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.database import session_scope
from app.models import QuarantinedRequest
from app.metrics import REJECTED
logger = logging.getLogger("app.errors")
def _error_body(request: Request, code: str, message: str, details: Any = None):
    return {"error": {"code": code, "message": message, "details": details, "request_id": getattr(request.state, "request_id", None)}}
def register_error_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        details = [{"type": e.get("type"), "loc": list(e.get("loc", ())), "msg": e.get("msg")} for e in exc.errors()]
        try:
            body = await request.body()
            try: payload = json.loads(body.decode("utf-8"))
            except Exception: payload = {"_raw_body": body[:10000].decode("utf-8", errors="replace")}
            client = request.client.host if request.client else "unknown"
            with session_scope() as session:
                session.add(QuarantinedRequest(client_id=client, payload_json=json.dumps(payload)[:20000], field_errors_json=json.dumps(details), request_id=getattr(request.state, "request_id", None)))
            REJECTED.inc()
        except Exception:
            logger.exception("Failed to persist quarantined request")
        return JSONResponse(status_code=422, content=_error_body(request, "validation_error", "Request validation failed; record quarantined.", details))
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        message = str(exc.detail) if isinstance(exc.detail, str) else "HTTP request failed."
        return JSONResponse(status_code=exc.status_code, headers=exc.headers, content=_error_body(request, "http_error", message))
    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled API error", extra={"request_id": getattr(request.state, "request_id", None)})
        return JSONResponse(status_code=500, content=_error_body(request, "internal_server_error", "An unexpected error occurred."))
