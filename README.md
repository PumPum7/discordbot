# Discord Bot

A general utility discord bot with multi server support. 

## Features

- Economy system
- Exp system with generated images and leveled roles
- A lot of settings for the server and the individual user

## Setup

To run this bot yourself you have to prepare a few things:
1. Download and set up [Redis](https://redis.io/download)
2. Download and set up [MongoDB](https://www.mongodb.com/try/download/community)
3. Create a bot_settings.py file (this will probably be changed in the future) with the following content:
```py
token = ""  # just paste the bot token in here
prefix = ["."]  # multiple prefixes are possible
default_game = ["games here"]  # can be anything, just follow the format
database_username = ["this can be empty", "username"]  # the database username of your mongodb database
database_password = ["this can be empty", "password"]  # the database password of your mongodb database
database_default = "database name"  # the default database which will be used
database_url = ["this can be empty", "database url"]  # the database url which will be used 
embed_color: int = 0xB0D2E7  # the default embed color
currency_name = "$"  # the name of the currency (this is not a server setting currently)
redis_settings = {"url": ("the redis url", host as int)}  # your redis settings (you might need more than the url here)
default_exp = {
    "exp_amount": 20,
    "exp_cooldown": 60,
    "exp_blacklist_roles": None,
    "exp_level_roles": None,
}  # the default exp settings
default_income = {
    "income_amount": 10,
    "income_cooldown": 60,
    "income_daily": 200,
    "income_hourly_cooldown": 24,
    "income_blacklist_roles": None,
    "income_multiplier_roles": None,
    "income_tax_roles": None,
    "income_give_disallowed_roles": None,
    "income_give_allowed_roles": None
}  # default income settings

grpc_settings = {
    "address": "localhost:50051"
}  # the grpc settings used for microservices 
limits = {
    "basic": {
        "exp_level_roles": 10
    }
}  # limits which could be used for a subscription based model
subscription_website = "website to donate"  # a donation website to your bot if users hit limits
# dont change this setting, this currently is needed for the way settings are handled
third_value_settings = ["income_tax_roles", "income_multiplier_roles", "exp_level_roles"] 
# you can change the emotes used for numbers here, make sure the bot has access to them:
digits = {
            10: ":keycap_10:",
            9: ":nine:",
            8: ":eight:",
            7: ":seven:",
            6: ":six:",
            5: ":five:",
            4: ":four:",
            3: ":three:",
            2: ":two:",
            1: ":one:"
        }

```

3. Download the required python libraries from the requirements.txt file
4. Download the grpc backend: _will be added once the bot is completely ready_
5. Run the bot, it will automatically load all files starting with cmd

> This bot is not ready for production usage, which also is the usage why the GRPC files and the GRPC client are not open source yet.