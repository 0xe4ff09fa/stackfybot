from src.interfaces.api.middlewares import get_current_user
from fastapi import APIRouter, Depends
from src import database

# Initialize APIRouter
router = APIRouter()

@router.get("/api/v1/transactions")
def get_transactions(
    page: int = 1,
    size: int = 10,
    current_user: str = Depends(get_current_user)):
    txs = []
    for tx in (
        database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.user == current_user) &
            (database.RampBUYAndSELL.status != "created"))
        .order_by(database.RampBUYAndSELL.updated_at.desc())
        .limit(25)
        .paginate(page, size)):
        txs.append({
            "txid": str(tx.id),
            "type": str(tx.order_type),
            "status": str(tx.status),
            "from": {
                "btc": tx.value_from_btc,
                "brl": tx.value_from_brl
            },
            "to": {
                "btc": tx.value_to_btc,
                "brl": tx.value_to_brl
            },
            "price": tx.price_services,
            "fee": tx.fee_value,
            "identifier": tx.identifier,
            "created_at": tx.created_at.strftime("%d/%m/%Y %H:%M"),
            "updated_at": tx.updated_at.strftime("%d/%m/%Y %H:%M")
        })
    return txs