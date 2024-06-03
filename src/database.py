from playhouse.migrate import PostgresqlMigrator, MySQLMigrator, SqliteMigrator, migrate
from src.configs import DatabaseConfig
from datetime import datetime
from secrets import token_hex
from peewee import (
    PostgresqlDatabase,
    SqliteDatabase,
    FloatField,
    Model,
    TextField,
    BooleanField,
    DateTimeField,
    ForeignKeyField
)
from uuid import uuid4

import logging

class CustomPostgresqlDatabase(PostgresqlDatabase):
    configs = DatabaseConfig

    def execute_sql(self, sql, params=None, commit=None):
        """
        Execute the specified SQL statement with optional parameters and commit the changes.

        Args:
            sql (str): The SQL statement to execute.
            params (tuple, optional): The parameters to substitute in the SQL statement. Defaults to None.
            commit (bool, optional): Whether to commit the changes. Defaults to None.
        """
        try:
            super().execute_sql("SELECT 1;", params, commit)
        except Exception as error:
            logging.error(str(error), exc_info=True)
            if "password" in str(error):
                super().__init__(
                    database=self.configs.DB_NAME,
                    host=self.configs.DB_HOST,
                    port=self.configs.DB_PORT,
                    user=self.configs.DB_USER,
                    password=self.configs.DB_PASS,
                    autorollback=True,
                    thread_safe=True,
                    autoconnect=True,
                )
            else:
                self.close()
                self.connect()

        return super().execute_sql(sql, params, commit)

class GenericDatabase:
    INSTANCE = None

    def __init__(self, configs: DatabaseConfig):
        """
        Initialize the GenericDatabase class.

        Args:
            configs (DatabaseConfig): The database configurations.
        """
        self.configs = configs
        if "postgres" in self.configs.DB_TYPE:
            self.INSTANCE = CustomPostgresqlDatabase(
                database=self.configs.DB_NAME,
                host=self.configs.DB_HOST,
                port=self.configs.DB_PORT,
                user=self.configs.DB_USER,
                password=self.configs.DB_PASS,
                autorollback=True,
                thread_safe=True,
                autoconnect=True,
            )
            self.INSTANCE.configs = self.configs
        else:
            self.INSTANCE = SqliteDatabase(
                database=configs.DB_NAME.split(".")[0] + "." + "sqlite"
            )

class AutoMigration:
    
    def __init__(self, configs: object) -> None:
        if (configs.DB_TYPE == "postgres"):
            self.migrator = PostgresqlMigrator(database)
        elif (configs.DB_TYPE == "mysql"):
            self.migrator = MySQLMigrator(database)
        else:
            self.migrator = SqliteMigrator(database)
    
    def execute(self):
        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "date_of_birth", 
                    TextField(null=True)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "last_name", 
                    TextField(null=True)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "level", 
                    TextField(null=True)
                ),
            ).execute()
        except:
            pass
        
        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "is_operation", 
                    BooleanField(default=False)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "is_partner", 
                    BooleanField(default=False)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "is_affiliate", 
                    BooleanField(default=False)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "accepted_term", 
                    BooleanField(default=False)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "user", 
                    "accepted_term_date", 
                    DateTimeField(default=datetime.now)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "rampbuyandsell", 
                    "operator", 
                    TextField(null=True)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "rampbuyandsell", 
                    "bank", 
                    TextField(null=True)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "rampbuyandsell", 
                    "nfse", 
                    BooleanField(default=False)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "rampbuyandsell", 
                    "affiliate_code", 
                    TextField(null=True)
                ),
            ).execute()
        except:
            pass

        try:
            migrate(
                self.migrator.add_column(
                    "identificationdocument", 
                    "document_name", 
                    TextField(null=True)
                ),
            ).execute()
        except:
            pass
    
database = GenericDatabase(configs=DatabaseConfig()).INSTANCE

class BaseModel(Model):
    class Meta:
        database = database

class User(BaseModel):
    id = TextField(unique=True, primary_key=True, default=uuid4)
    email = TextField(null=True)
    origin = TextField(null=True)
    level = TextField(null=True)
    is_admin = BooleanField(default=False)
    is_partner = BooleanField(default=False)
    is_affiliate = BooleanField(default=False)
    is_operation = BooleanField(default=False)
    date_of_birth = TextField(null=True)
    accepted_term = BooleanField(default=False)
    accepted_term_date = DateTimeField(default=datetime.now)
    username = TextField(null=True)
    first_name = TextField(null=True)
    last_name = TextField(null=True)
    is_blocked = BooleanField(default=False)
    affiliated_to = TextField(null=True)
    affiliate_code = TextField(null=True, default=lambda : token_hex(4).upper())
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """
        Save the User model instance with updated timestamps.
        """
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

class PaymentAddresses(BaseModel):
    id = TextField(unique=True, primary_key=True, default=uuid4)
    user = ForeignKeyField(User)
    lightning_address = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """
        Save the PaymentAddresses model instance with updated timestamps.
        """
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

class IdentificationDocument(BaseModel):
    id = TextField(unique=True, primary_key=True, default=uuid4)
    user = ForeignKeyField(User)
    status = TextField(default="pending", choices=["pending", "analysis", "approved", "rejected"])
    document_type = TextField(null=True)
    document_name = TextField(null=True)
    document_number = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """
        Save the IdentificationDocument model instance with updated timestamps.
        """
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

class BankAccount(BaseModel):
    alias = TextField(unique=True, primary_key=True)
    name = TextField(null=True)
    operator = TextField(null=True)
    activated = BooleanField(default=False)
    address = TextField(null=True)
    bank_name = TextField(null=True)
    account_type = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """
        Save the BankAccount model instance with updated timestamps.
        """
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

class RampBUYAndSELL(BaseModel):
    id = TextField(unique=True, primary_key=True, default=uuid4)
    user = ForeignKeyField(User)
    bank = TextField(null=True, default=None)
    status = TextField(default="created", choices=["created", "pending", "cancelled", "settled"])
    operator = TextField(null=True)
    value_from_btc = FloatField(default=0)
    value_from_brl = FloatField(default=0)
    value_to_btc = FloatField(default=0)
    value_to_brl = FloatField(default=0)
    price_services = FloatField(default=0)
    price_provider = FloatField(default=0)
    fee_value = FloatField(default=0)
    fee_rate_price = FloatField(default=0)
    fee_rate_services = FloatField(default=0)
    fee_rate_provider = FloatField(default=0)
    nfse = BooleanField(default=False)
    order_type = TextField(default="BUY", choices=["BUY", "SELL"])
    identifier = TextField(default=lambda: token_hex(4).upper())
    receipt_path = TextField(null=True)
    affiliate_code = TextField(null=True)
    expiry_at = DateTimeField(default=datetime.now)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """
        Save the RampBUYAndSELL model instance with updated timestamps.
        """
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

class RampAddressInfo(BaseModel):
    id = TextField(unique=True, primary_key=True, default=uuid4)
    ramp = ForeignKeyField(RampBUYAndSELL)
    alias = TextField(null=True)
    address = TextField(null=True)
    network = TextField(null=True, choices=["lightning", "bitcoin", "pix"])
    channel = TextField(null=True)
    state = TextField(null=True)
    country = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """
        Save the RampAddressInfo model instance with updated timestamps.
        """
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

def create_tables():
    """
    Create tables in the database.
    """
    AutoMigration(configs=DatabaseConfig()).execute()
    database.create_tables([
        User, 
        PaymentAddresses,
        BankAccount,
        RampBUYAndSELL, 
        RampAddressInfo,
        IdentificationDocument
    ], safe=True)
