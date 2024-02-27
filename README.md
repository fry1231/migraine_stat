# Migrebot
https://t.me/ourmigren_bot

Migrebot is a tool that allows users to track their headaches, migraine episodes and medication usage. This bot is designed to help users monitor their headaches and medications, providing insights and awareness into their health patterns.

## Table of Contents
- [General Informaion](#general-information)
  - [Configuration](#configuration)
  - [Database](#database)
  - [CICD Pipeline](#cicd-pipeline)
  - [User states in Redis](#user-states-in-redis)
    - [Redis Channels](#redis-channels)
- [Usage](#usage)
  - [Bot Commands](#bot-commands)
  - [Features](#other-features)
- [Roadmap](#roadmap)


## General Information

### Configuration

Environmental variables set up is required for the bot to work correctly.  
Modify a `.env` file in the project root directory or add the following variables
to the CICD pipeline:

```ini
API_TOKEN=telegram API token
POSTGRES_USER=postgres
POSTGRES_PASS=postgres
IN_PRODUCTION=0
MY_TG_ID=your telegram ID (chat_id) from the bot
```

### Database

The bot uses an Postgres database to store user data. 
The database dir is located at `postgres-data` and mounted as a docker volume
The schema is managed and updated through Alembic migrations. 
The Alembic directory is `db/alembic`.

### CICD Pipeline

CICD is realized using GitLab. The configuration is specified in the `.gitlab-ci.yml` file. To execute the pipeline, 
you need to set up the required environmental variables mentioned in the file or in the `.env` file.

### User states in Redis
Each time user enters a state in FSM (Finite State Machine), the state is reflected in the Redis.  
States are saved under `state:%FormName%:%StepNumber%:%StepName%` keys. Values are lists of users' id's.  
User's current_state (within fsm forms) is stored under the keys like `user_state:user_id`. Value is a string with 
the current state name.
All user states are stored under the keys 'state:*'. List of all available states are in fsm_forms/__init__.py

#### Redis Channels:

If some state is changing, a message is sent to `channel:states` to reflect the changes:
```json
{
  "user_id": 123,
  "user_state": "AddDrugForm:0:name",
  "action": "set", (or "unset")
  "incr_value": 1
}
```
Each subsequent message increments 'incr_value' by 1. Current increment value is stored under the 'incr_value' key.  
If 'incr_value' == 0, then the client needs to refresh all the states from API.

If everyday report is changed, message is sent to 'channel:report' to reflect the changes:
```json
{
  "n_notified_users": 0,
  "new_users": [...PydanticUser],
  "deleted_users": [...PydanticUser],
  "n_pains": 0,
  "n_druguses": 0,
  "n_pressures": 0,
  "n_medications": 0
}
```

## Usage

To start the bot using docker compose:
```bash
docker compose --env-file .env up -d
```

### Bot Commands

The bot responds to the following commands:


- `/pain`: Record a headache occurrence
- `/druguse`: Record medication usage
- `/pressure`: Record your blood pressure
- `/medications`: Add or remove the medications you are using
- `/calendar`: Change records in the calendar
- `/statistics`: Download your pain or medication statistics
- `/settings`: Customize the language and time of alerts

*Admin commands:* (work only for the user with `chat_id=$MY_TG_ID`)
- `/announcement`: Create and send an announcement to different users groups
- `/token`: Update token for YandexDisk API (for backups)
- `/backup`: Create a backup of the database and send it to YandexDisk
- `/report`: Send a daily report to the owner
- `/write`: Write a message to the user by his chat_id


### Other Features
If someone is writing a message to the bot, it would be forwared to the owner. 
Owner can reply to it, using native telegram reply. 
For now, bot support only text for such messages.



## Roadmap

Here are some of the planned features and improvements for the bot:

   - ~~Support for multiple languages~~
   - Switching to ~~Postgres~~, Aiogram 3
   - Advanced analytic reports based on user data
   - Enhancing data visualization with graphs and charts for better insights
   - Notification of medication overuse
   - Lifestyle recommendations to reduce the incidence of headaches
