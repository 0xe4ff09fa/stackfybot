from src.interfaces.api.middlewares import get_user_without_kyc_validation
from src.interfaces.chat.telegram import bot
from src.interfaces.api.schemas import RegistrationBasicKYCSchema, UserSchema
from src.interfaces.chat.notify import Notify
from src.services.firebase import sign_in_with_password, send_email_password_reset_link, auth
from src.configs import SECRET_KEY
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from time import time
from src import database

import logging
import jwt

# Initialize APIRouter
router = APIRouter()

@router.post("/api/v1/signup")
async def signup(data: UserSchema):
    try:
        uid = auth.create_user(
            email=data.email, 
            password=data.password
        ).uid
        database.User.create(
            id=uid,
            email=data.email,
            username=data.email.split("@")[0]
        )
        return { "id": uid }
    except Exception as error:
        logging.error(str(error), exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating user account")

@router.put("/api/v1/kyc")
async def basic_kyc(
        data: RegistrationBasicKYCSchema,         
        background_tasks: BackgroundTasks,
        current_user: str = Depends(get_user_without_kyc_validation)):
    if database.IdentificationDocument.select(
        database.IdentificationDocument.status
    ).where(
        (database.IdentificationDocument.user == current_user) &
        (database.IdentificationDocument.document_type == "CPF")
    ).exists():
        raise HTTPException(409)
    
    user = database.User.get(id=current_user)
    user.first_name = data.first_name
    user.last_name = data.last_name
    user.date_of_birth = data.date_of_birth
    user.save()

    full_name = f"{data.first_name} {data.last_name}".title()
    database.IdentificationDocument.create(
        user=current_user,
        status="pending",
        document_type="CPF",
        document_number=data.document_id,
        document_name=full_name
    )

    background_tasks.add_task(
        func=Notify.notify_new_user_verification,
        bot=bot,
        username=user.username,
        email=user.email,
        full_name=full_name,
        cpf=data.document_id,
        date_of_birth=data.date_of_birth
    )
    return { "message": "Data updated successfully." }

@router.post("/api/v1/token")
async def generate_token(data: UserSchema):
    try:
        user = sign_in_with_password(data.email, data.password)
        expr = time() + 86400
        token = jwt.encode({ "sub": user["localId"], "email": user["email"], "exp": expr }, SECRET_KEY, algorithm="HS256")
        return { "access_token": token, "token_type": "bearer" }
    except Exception as error:
        logging.error(str(error), exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/api/v1/reset-password")
async def reset_password(email: str):
    try:
        send_email_password_reset_link(email)
        return { "message": "Password recovery email sent successfully." }
    except Exception as error:
        logging.error(str(error), exc_info=True)
        return { "message": "Password recovery email sent successfully." }
