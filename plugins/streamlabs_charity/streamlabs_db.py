import psycopg2
import datetime

from models.globals import get_global

class Streamlabs_DB:
    def __init__(self, plugin_name, config_parser):
        self.plugin_name = plugin_name
        self.config_parser = config_parser
        self.connection = psycopg2.connect(
            host=self.config_parser[self.plugin_name]['db_host'],
            port=self.config_parser[self.plugin_name]['db_port'],
            user=self.config_parser[self.plugin_name]['db_user'],
            password=self.config_parser[self.plugin_name]['db_password'],
            dbname=self.config_parser[self.plugin_name]['db_name']
        )

        self.cursor = self.connection.cursor()

        # Crée le schéma et les tables si elles n'existent pas en DB
        query = f"select * from information_schema.schemata where schema_name = '{self.plugin_name}'"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if not result:
            self.cursor.execute(f"CREATE SCHEMA {self.plugin_name}")
            self.cursor.execute(f"CREATE TABLE {self.plugin_name}.donations (id SERIAL PRIMARY KEY, username VARCHAR(255), donation_amount decimal, donation_time TIMESTAMP, stream_session text)")
            self.connection.commit()


    def add_donation(self, username, donation):
        cursor = self.connection.cursor()
        timestamp = datetime.datetime.now()
        cursor.execute(f"INSERT INTO {self.plugin_name}.donations (username, donation_amount, donation_time, stream_session) VALUES (%s, %s, %s, %s)", (username, donation, timestamp, get_global('current_stream_session')))
        self.connection.commit()


    def get_all_donations_for_current_session(self) -> str:
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT username, donation_amount FROM {self.plugin_name}.donations WHERE stream_session = %s", (get_global('current_stream_session'),))
        res = cursor.fetchall()
        return '\n'.join([f'{don[0]} a donné {don[1]}€' for don in res])
    