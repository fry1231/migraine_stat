# Migrebot
https://t.me/ourmigren_bot

Migrebot is a tool that allows users to track their headaches, migraine episodes and medication usage. This bot is designed to help users monitor their headaches and medications, providing insights and awareness into their health patterns.

## Table of Contents
- [Getting Started](#getting-started)
  - [Configuration](#configuration)
  - [Database](#database)
  - [CICD Pipeline](#cicd-pipeline)
- [Usage](#usage)
  - [Bot Commands](#bot-commands)
  - [Features](#features)
- [Roadmap](#roadmap)


## Getting Started

### Configuration

You need to set up the required environmental variables for the bot to work correctly. 
Modify a `.env` file in the project root directory or add the following variables
to your CICD pipeline:

```ini
API_TOKEN=telegram API token
RABBITMQ_USER=guest
RABBITMQ_PASS=guest
RABBITMQ_HOST=rabbitmq
POSTGRES_USER=postgres
POSTGRES_PASS=postgres
MY_TG_ID=your telegram ID (chat_id) from the bot
```

## Database

The bot uses an SQLite database to store user data. 
The database file is located at `db/db_file/sql_app.db` and mounted as a docker volume
The data is managed and updated through Alembic migrations. 
The Alembic directory is `db/alembic`.

## CICD Pipeline

CICD is realized using GitLab. The configuration is specified in the `.gitlab-ci.yml` file. To execute the pipeline, you need to set up the required environmental variables mentioned in the file or in the `.env` file.

## Usage

To start the bot use docker compose:
```bash
docker compose up -d
```

### Bot Commands

The bot responds to the following commands:

- `/reschedule`: Set the frequency of headache tracking surveys
- `/pain`: Record a headache occurrence
- `/druguse`: Record medication usage
- `/check_pains`: View statistics on headache occurrences
- `/check_drugs`: View statistics on medication usage
- `/add_drug`: Add a new medication to the list of available drugs

*Admin commands:* (work only for the user with `chat_id=$MY_TG_ID`)
- `/download_db`: Download SQLite database instance
- `/execute_raw`: Execute SQL query from the message


### Features
If someone is writing a message to the bot, it would be forwared to the owner. 
Owner can reply to it, using native telegram reply. 
For now, bot support only text for such messages.



## Roadmap

Here are some of the planned features and improvements for the bot:

   - Support for multiple languages
   - Switching to Postgres, Aiogram 3
   - Advanced analytic reports based on user data
   - Enhancing data visualization with graphs and charts for better insights
   - Notification of medication overuse
   - Lifestyle recommendations to reduce the incidence of headaches
