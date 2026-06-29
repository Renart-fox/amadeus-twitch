import aiohttp

from models.amadeus_plugin import AmadeusPlugin
from config.amadeus_config import Amadeus_Config
from models.decorators import on_follow, on_load, on_chat_message, on_custom_message, on_stream_start, CustomMessage, on_stream_update
from models.globals import set_global, get_global
from models.signal_manager import emit_signal

from threading import Thread

PLUGIN_NAME = "amadeus_discord"

class Amadeus_Discord(AmadeusPlugin):

    plugin_name = PLUGIN_NAME
    client = None

    def __init__(self) -> None:
        super().__init__()

        self.config_parser.set(self.plugin_name, 'client_id', '')
        self.config_parser.set(self.plugin_name, 'client_secret', '')
        self.config_parser.set(self.plugin_name, 'token', '')
        self.config_parser.set(self.plugin_name, 'webhook', '')

        self.write_config(overwrite=False)
        self.read_config()


    @on_stream_start
    async def on_stream_start(self):
        from discord import Webhook

        category = get_global('current_category')
        stream_title = get_global('stream_title')

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.config_parser[self.plugin_name]['webhook'],
                                        session=session,
                                        bot_token=self.config_parser[self.plugin_name]['token'])
            ROLE_CODE = '<@&1513375155643220010>'
            ROLE_DIVERS = '<@&1513375235435532479>'
            ROLE_JEUX = '<@&1513375194897715323>'
            ROLE_TOUT = '<@&1513375278964019312>'
            main_role = ROLE_JEUX
            main_role = ROLE_CODE if 'software' in category.lower() else main_role
            await webhook.send(f'{ROLE_TOUT} {main_role} Miel lance un live sur {category} ! - {stream_title} - {Amadeus_Config().channel_url}')

    
    @on_stream_update
    async def on_stream_update(self):
        from discord import Webhook

        category = get_global('current_category')
        stream_title = get_global('stream_title')

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.config_parser[self.plugin_name]['webhook'],
                                        session=session,
                                        bot_token=self.config_parser[self.plugin_name]['token'])
            ROLE_CODE = '<@&1513375155643220010>'
            ROLE_DIVERS = '<@&1513375235435532479>'
            ROLE_JEUX = '<@&1513375194897715323>'
            ROLE_TOUT = '<@&1513375278964019312>'
            main_role = ROLE_JEUX
            main_role = ROLE_DIVERS if 'just chatting' in category.lower() else main_role
            main_role = ROLE_CODE if 'software' in category.lower() else main_role
            await webhook.send(f'{ROLE_TOUT} {main_role} Miel on change de catégorie et on part sur {category} ! - {stream_title} - {Amadeus_Config().channel_url}')


    @on_custom_message
    async def on_custom_message(self, message):
        if message.from_plugin == 'amadeus_ai':
            if message.data['type'] == 'amadeus_discord_message':
                msg = message.data['message']
                await msg.reply(message.data['content'])


    def handle_discord_bot(self):
        import discord
        from discord import Message

        intents = discord.Intents.default()
        intents.message_content = True

        self.client = discord.Client(intents=intents)
        client = self.client

        @self.client.event
        async def on_ready():
            print(f'[{self.plugin_name}] We have logged in as {self.client.user}') # type: ignore

        @self.client.event
        async def on_message(message: Message):
            users_mentionned = [u.id for u in message.mentions]
            thread_history = []
            
            previous_message = message.reference
            while previous_message is not None:
                old_message = await message.channel.fetch_message(previous_message.message_id) # type: ignore
                users_mentionned += [u.id for u in old_message.mentions]
                thread_history = [f'{old_message.author.display_name} a dit : {old_message.clean_content}'] + thread_history
                previous_message = old_message.reference

            thread_history.append(f'{message.author.display_name} a dit : {message.clean_content}')
            
            content = 'Amadeus, voici un historique de messages Discord. Tu y es désormais connectée, et ta réponse sera directement envoyé sur le salon Discord de Miel. Sur Discord, Miel est identifiée comme Mielikki.'
            content += '\n'.join(thread_history)

            if 742665381516279863 in users_mentionned and message.author.id != 742665381516279863:
                print(f'Read message from {message.author.display_name} saying {message.clean_content}')
                c = CustomMessage(self.plugin_name, {
                    'type': 'discord_message',
                    'message': message,
                    'content': content
                },
                'amadeus_ai')
                await emit_signal('on_custom_message', c)

        self.client.run(self.config_parser[self.plugin_name]['token'])



    @on_load
    async def on_load(self):
        thread = Thread(target=self.handle_discord_bot, daemon=True)
        thread.start()



exported_class = Amadeus_Discord