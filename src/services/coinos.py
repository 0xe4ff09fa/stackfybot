from src.configs import COINOS_PASSWORD, COINOS_USERNAME
from coinos import Coinos

coinos = Coinos(
    username=COINOS_USERNAME,
    password=COINOS_PASSWORD
)
