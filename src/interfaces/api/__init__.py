from fastapi.middleware.cors import CORSMiddleware
from src.interfaces.chat import telegram
from src.interfaces.api import health, quote, trade, account, transactions
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from src.configs import API_HOST, API_PORT, PRODUCTION, TelegramConfig
from fastapi import FastAPI, Request

import uvicorn

# Initialize API.
api = FastAPI(
    docs_url=("/docs" if not PRODUCTION else None), 
    redoc_url=None, 
    swagger_ui_oauth2_redirect_url=None,
    openapi_url=("/openapi.json" if not PRODUCTION else None)
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api.include_router(account.router)
api.include_router(health.router)
api.include_router(quote.router)
api.include_router(transactions.router)
api.include_router(trade.router)

@api.exception_handler(HTTPException)
def HTTPExceptionHandler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})

@api.post("/api/v1/webhook/telegram", include_in_schema=False)
def telegram_webhook(data: dict, request: Request):
    headers = request.headers
    if headers.get("x-telegram-bot-api-secret-token") != TelegramConfig().WEBHOOK_KEY:
        raise HTTPException(401)
    else:
        print(data)
        telegram.loads_updates(data)

def start():
    uvicorn.run(
        api,
        host=API_HOST,
        port=API_PORT,
        loop="asyncio",
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(asctime)s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "foo-logger": {"handlers": ["default"], "level": "DEBUG"},
            },
        },
    )
