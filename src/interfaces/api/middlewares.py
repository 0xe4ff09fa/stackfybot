from fastapi.security import HTTPBearer
from src.configs import KYC_VERIFICATION, SECRET_KEY
from fastapi import Depends, HTTPException
from src import database

import logging
import jwt

def get_user_without_kyc_validation(token: str = Depends(HTTPBearer())):
    try:
        token = jwt.decode(
            jwt=token.credentials, 
            key=SECRET_KEY, 
            algorithms=["HS256"]
        )
        email = token.get("email")
        sub = token.get("sub")
        if not sub:
            raise HTTPException(status_code=401)
        
        user = database.User.get_or_create(id=sub)
        user[0].username = email.split("@")[0]
        user[0].email = email
        user[0].save()
        
        if user[0].is_blocked == True:
            raise HTTPException(status_code=401)
        return sub
    except Exception as error:
        logging.error(str(error), exc_info=True)
        raise HTTPException(status_code=401)

def get_current_user(token: str = Depends(HTTPBearer())):
        try:
            token = jwt.decode(
                jwt=token.credentials, 
                key=SECRET_KEY, 
                algorithms=["HS256"]
            )
            email = token.get("email")
            sub = token.get("sub")
            if not sub:
                raise HTTPException(status_code=401)

            user = database.User.get_or_create(id=sub)
            user[0].username = email.split("@")[0]
            user[0].email = email
            user[0].save()

            if user[0].is_blocked == True:
                raise HTTPException(status_code=401)
        except Exception as error:
            logging.error(str(error), exc_info=True)
            raise HTTPException(status_code=401)

        if KYC_VERIFICATION:
            identification_document = database.IdentificationDocument.select(
                    database.IdentificationDocument.status
            ).where(
                (database.IdentificationDocument.user == sub) &
                (database.IdentificationDocument.document_type == "CPF")
            ) 
            if identification_document.exists():
                identification_document_status = identification_document.get().status
                if (identification_document_status != "approved"):
                    raise HTTPException(status_code=423)
            else:
                raise HTTPException(status_code=403, detail="Access denied. KYC has not been completed.")
        
        return sub
