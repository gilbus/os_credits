from os import environ

from dotenv import load_dotenv

__version__ = "0.1.0"

load_dotenv()

PERUN_RPC_BASE_URL = "https://perun.elixir-czech.cz/krb/rpc/json/"

try:
    SERVICE_USER_LOGIN = environ["SERVICE_USER_LOGIN"]
    SERVICE_USER_PASSWORD = environ["SERVICE_USER_PASSWORD"]
    VO_ID = int(environ["VO_ID"])
except KeyError as e:
    print(f"Missing environment variable {e}. Aborting")
    exit(1)
