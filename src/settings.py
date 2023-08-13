import os


IS_TESTING = True if int(os.getenv('IS_TESTING', default='0')) == 1 else False
API_TOKEN = os.getenv('API_TOKEN')

MY_TG_ID = os.getenv('MY_TG_ID')
if MY_TG_ID is not None:
    MY_TG_ID = int(MY_TG_ID)

POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASS = os.getenv('POSTGRES_PASS')
PAYMENTS_TOKEN_RU = os.getenv('PAYMENTS_TOKEN_RU')
