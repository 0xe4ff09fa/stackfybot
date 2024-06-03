from fastapi.responses import JSONResponse
from src.services import redis
from fastapi import APIRouter
from src import database

import logging

# Initialize APIRouter
router = APIRouter()

@router.get("/health/liveness", include_in_schema=False)
def health_liveness():
    return JSONResponse({"liveness": True})

@router.get("/health/readiness", include_in_schema=False)
def health_readiness():
    readiness = True
    try:
        database.execute_sql("SELECT 1;")
    except Exception as error:
        logging.error(str(error), exc_info=True)
        readiness = False

    try:
        redis.INSTANCE.ping()
    except Exception as error:
        logging.error(str(error), exc_info=True)
        readiness = False

    return JSONResponse({"readiness": readiness}, status_code=(200 if (readiness) else 503))
