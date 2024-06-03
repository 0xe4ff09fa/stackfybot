from flagsmith import Flagsmith
from os import getenv

# Initialize an instance of the 
# Flagsmith
flagsmith = Flagsmith(
    environment_key=getenv("FLAGSMITH_KEY"), 
    environment_refresh_interval_seconds=60 * 5
)

try:
    flags = flagsmith.get_environment_flags()
except:
    flags = None
