import os


IS_TESTING = True if int(os.getenv('IS_TESTING', default='0')) == 1 else False
API_TOKEN = os.getenv('API_TOKEN')
MY_TG_ID = int(os.getenv('MY_TG_ID'))
