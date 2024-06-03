from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from typing import Optional

class UserSchema(BaseModel):
    email: str
    password: str

class RegistrationBasicKYCSchema(BaseModel):
    first_name: str
    last_name: str
    document_id: str
    date_of_birth: str

    @validator("document_id")
    def validate_document_id(cls, document_id: str):
        document_id = document_id.replace(".", "").replace("-", "")
        if len(document_id) < 11:
            raise ValueError("Document ID is invalid.")
        return document_id

    @validator("date_of_birth")
    def validator_date_of_birth(cls, date_of_birth: str):
        date_of_birth = date_of_birth.replace("-", "/")
        try:
            birth_date = datetime.strptime(date_of_birth, "%Y/%m/%d")
            eighteen_years_ago = datetime.now() - timedelta(days=365 * 18)

            if birth_date > eighteen_years_ago:
                raise ValueError("The person must be at least 18 years old.")

            return date_of_birth
        except:
            raise ValueError("The date of birth format is wrong, it should be d/m/Y")

class AddressSchema(BaseModel):
    address: str
