from src.services.redis import redis
from src import database

class BankAccount:

    def listing_bank_accounts(activated=None):
        banks = []
        for bank in database.BankAccount.select(): 
            if activated == None:
                banks.append({
                    "operator": bank.operator,
                    "name": bank.name,
                    "alias": bank.alias,
                    "address": bank.address,
                    "activated": bank.activated,
                    "bank_name": bank.bank_name,
                    "account_type": bank.account_type
                })
            
            if activated == bank.activated:
                banks.append({
                    "operator": bank.operator,
                    "name": bank.name,
                    "alias": bank.alias,
                    "address": bank.address,
                    "activated": bank.activated,
                    "bank_name": bank.bank_name,
                    "account_type": bank.account_type
                })

        return banks

    def select_account_bank_current(alias: str):
        bank = BankAccount.get_account_bank(alias)
        if not bank.get("activated"):
            raise Exception("Account was not deactivated.")
        
        redis.redis_set("bank.current", bank)
        return bank

    def get_account_bank_current():
        return redis.redis_get("bank.current")

    def get_account_bank(alias: str):
        bank = database.BankAccount.select().where(
            (database.BankAccount.alias == alias))
        if not bank.exists():
            raise Exception("Bank account does not exist.")
        else:
            bank = bank.get()
        
        return {
            "operator": bank.operator,
            "name": bank.name,
            "alias": bank.alias,
            "address": bank.address,
            "activated": bank.activated,
            "bank_name": bank.bank_name,
            "account_type": bank.account_type
        }

    def active_or_disable_account_bank(alias: str):
        bank = database.BankAccount.select().where(
            (database.BankAccount.alias == alias)
        )
        if not bank.exists():
            raise Exception("Bank account does not exist.")
        else:
            bank = bank.get()
            activated = (False if bank.activated else True)
            bank.activated = activated
            bank.save()
            return {
                "operator": bank.operator,
                "name": bank.name,
                "alias": bank.alias,
                "address": bank.address,
                "activated": activated,
                "bank_name": bank.bank_name,
                "account_type": bank.account_type
            }
    
    def add_bank_account(
        operator: str,
        name: str,
        alias: str,
        address: str,
        bank_name: str,
        account_type: str
    ):
        """
        Add a new bank account to the database.

        Args:
            id (str): The identifier user.
            name (str): The name associated with the bank account.
            alias (str): The alias or nickname for the bank account.
            address (str): The address or PIX key associated with the bank account.
            bank_name (str): The name of the bank.
            account_type (str): The type of the bank account.
        """
        if database.BankAccount.select().where(
            (database.BankAccount.alias == str(alias))
        ).exists():
            raise Exception("Bank account already exists.")
        else:
            database.BankAccount.create(
                operator=operator,
                name=name,
                alias=alias,
                address=address,
                bank_name=bank_name,
                activated=True,
                account_type=account_type
            )
            return {"message": "Bank added successfully."}
