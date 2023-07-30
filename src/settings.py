import os


IS_TESTING = True if int(os.getenv('IS_TESTING')) == 1 else False
API_TOKEN = os.getenv('API_TOKEN')
