import psycopg2

class Amadeus_DB:
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

        print('db connection established')

        self.cursor = self.connection.cursor()

        # Crée le schéma et les tables si elles n'existent pas en DB
        query = f"select * from information_schema.schemata where schema_name = '{self.plugin_name}'"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if not result:
            self.cursor.execute(f"CREATE SCHEMA {self.plugin_name}")
            self.cursor.execute(f"CREATE TABLE {self.plugin_name}.users (id SERIAL PRIMARY KEY, twitch_id VARCHAR(255) UNIQUE, username VARCHAR(255), summary TEXT, last_interaction TIMESTAMP)")
            self.connection.commit()


    def get_user_summary_by_id(self, id):
        """_summary_
            Récupère le résumé d'un utilisateur par son id Twitch
        Args:
            id (int): Twitch ID

        Returns:
            str: Le résumé trouvé en BDD, ou une phrase tampon
        """
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT username, summary FROM {self.plugin_name}.users WHERE twitch_id = '{id}'")
        res = cursor.fetchone()
        if res is not None:
            return f"Voilà ce que je sais de l'utilisateur·ice {res[0]} :\n{res[1]}" # type: ignore
        else:
            return f"Je ne connais pas encore l'utilisateur·ice"


    def get_user_summary_by_username(self, username: str):
        """_summary_
            Récupère le résumé d'un utilisateur par son username Twitch
        Args:
            username (str): Username Twitch

        Returns:
            str: Le résumé trouvé en BDD, ou une phrase tampon
        """
        # Supprime le @ s'il est passé par erreur
        if username.startswith('@'):
            username = username[1:]
        
        cursor = self.connection.cursor()
        print(f"SELECT username, summary FROM {self.plugin_name}.users WHERE username = '{username}'")
        cursor.execute(f"SELECT username, summary FROM {self.plugin_name}.users WHERE username = '{username}'")
        res = cursor.fetchone()
        print(res)
        if res is not None:
            return f"Voilà ce que je sais de l'utilisateur·ice {res[0]} :\n{res[1]}" # type: ignore
        else:
            if 'amadeus' in username.lower():
                return ""
            return f"Je ne connais pas encore l'utilisateur·ice @{username}."