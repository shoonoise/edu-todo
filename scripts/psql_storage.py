import argparse

import psycopg2
import toml


def create_tables(conf):
    commands = (
        """
        DROP TABLE IF EXISTS lists CASCADE;
        """,
        """
        DROP TABLE IF EXISTS users CASCADE;
        """,
        """
        DROP TABLE IF EXISTS tasks CASCADE;
        """,
        """
        CREATE TABLE users (
        id serial PRIMARY KEY,
        name TEXT,
        password_md5 TEXT,
        default_list INTEGER
        )""",
        """
        CREATE TABLE lists (
        id serial PRIMARY KEY,
        description TEXT NOT NULL,
        user_id INT NOT NULL
        )""",
        """
        CREATE TABLE tasks (
        id serial PRIMARY KEY,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        created INTEGER NOT NULL,
        due_date INTEGER,
        notes TEXT,
        list_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL
        )""",
        """
        ALTER TABLE users
        ADD CONSTRAINT FK_default_list
        FOREIGN KEY (default_list) REFERENCES lists (id)
        """,
        """
        ALTER TABLE lists
        ADD CONSTRAINT FK_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
        """,
        """
        ALTER TABLE lists
        ADD CONSTRAINT uq_lists
        UNIQUE (user_id, description)
        """,
        """
        ALTER TABLE tasks
        ADD CONSTRAINT FK_list_id
        FOREIGN KEY (list_id) REFERENCES lists (id)
        """,
        """
        ALTER TABLE tasks
        ADD CONSTRAINT FK_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
        """
    )

    try:
        connection = psycopg2.connect(
            host=conf['database']['host'],
            user=conf['database']['user'],
            password=conf['database']['password'],
            dbname=conf['database']['db_name'],
            port=conf['database']['port']

        )
        connection.autocommit = True

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT version();"
            )

            print(f"Server version: {cursor.fetchone()}")

            for command in commands:
                cursor.execute(command)

    except Exception as ex:
        print('error', ex)
    finally:
        if connection:
            connection.close()
            print("PSQL conn closed")


if __name__ == "main":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file')
    args: argparse.Namespace = parser.parse_args()
    conf = toml.load(args.config)

    create_tables(conf)
