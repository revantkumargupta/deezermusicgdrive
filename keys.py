from decouple import Config, Csv

config = Config()

# Load the variables from the .env file
api_id = config('api_id')
api_hash = config('api_hash')
bot_token = config('bot_token')
arl_token = config('arl_token')
index_link = config('index_link')
db_url = config('db_url')
