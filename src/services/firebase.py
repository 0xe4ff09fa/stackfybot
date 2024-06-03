from firebase_admin import credentials, initialize_app, auth, storage
from src.configs import FIREBASE_ADMIN_CRED, FIREBASE_CLIENT_CRED
from json import loads

import requests
import logging

# Initialize Firebase
FIREBASE_CLIENT_CRED = loads(FIREBASE_CLIENT_CRED) if FIREBASE_CLIENT_CRED else {}
FIREBASE_ADMIN_CRED = loads(FIREBASE_ADMIN_CRED) if FIREBASE_ADMIN_CRED else {}
FIREBASE_ADMIN_CRED["private_key"] = FIREBASE_ADMIN_CRED.get("private_key", "").replace(r'\n', '\n')

try:
    firebase = initialize_app(
        credential=credentials.Certificate(
            cert=FIREBASE_ADMIN_CRED
        ),
        options={ 
            "storageBucket": FIREBASE_CLIENT_CRED.get("storageBucket") 
        }
    )
except Exception as error:
    logging.error(str(error), exc_info=True)
    firebase = None

def sign_in_with_password(
        email: str, 
        password: str, 
        returnSecureToken=False
    ) -> str:
    url = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword"
    res = requests.post(
        url, 
        params={
            "key" : FIREBASE_CLIENT_CRED["apiKey"]
        }, 
        json={
            "email": email, 
            "password": password, 
            "returnSecureToken": returnSecureToken
        }
    )
    res.raise_for_status()
    return res.json()

def send_email_password_reset_link(email: str) -> dict:
    url = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"
    res = requests.post(
        url, 
        params={
            "key" : FIREBASE_CLIENT_CRED["apiKey"]
        }, 
        json={
            "requestType": "PASSWORD_RESET",
            "email": email
        }
    )
    res.raise_for_status()
    return res.json()