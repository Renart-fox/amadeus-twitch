from typing import List

from models.amadeus_plugin import AmadeusPlugin
from models.decorators import on_follow, on_load, on_chat_message, on_custom_message, CustomMessage
from models.globals import set_global, get_global
from models.signal_manager import emit_signal
from config.amadeus_config import Amadeus_Config
from twitchAPI.twitch import Twitch
from twitchAPI.chat import ChatCommand, Chat

from pydantic_ai import Agent
from pydantic import dataclasses

from .data import amadeus_ai_personnality
from .amadeus_db import Amadeus_DB

PLUGIN_NAME = "amadeus_ai"


@dataclasses.dataclass
class Amadeus_FindUser():
    users_sumarries: List[str]


@dataclasses.dataclass
class Amadeus_Output():
    amadeus_response: str
    amadeus_facts_to_remember: str


class Amadeus(AmadeusPlugin):
    

    plugin_name = PLUGIN_NAME
    amadeus_agent : Agent


    def __init__(self) -> None:
        super().__init__()

        self.config_parser.set(self.plugin_name, 'anthropic_secret', '')

        self.write_config(overwrite=False)
        self.read_config()

        if self.active:
            self.db = Amadeus_DB(self.plugin_name, self.config_parser)


    async def retrieve_amadeus_data(self, cmd: ChatCommand):
        summary = self.db.get_user_summary_by_id(cmd.user.id)
        twitch_bot: Twitch = get_global('twitch_bot')
        await twitch_bot.send_whisper(from_user_id='1232194164', to_user_id=str(cmd.user.id), message=summary)


    @on_load
    async def on_load(self) -> None:
        await super().on_load()

        from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
        from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
        from pydantic_ai.providers.anthropic import AnthropicProvider

        self.amadeus_config = Amadeus_Config()
        
        self.model_provider = AnthropicProvider(api_key=self.config_parser[self.plugin_name]['anthropic_secret'])
        self.model = AnthropicModel('claude-haiku-4-5-20251001',
                            provider=self.model_provider,
                            settings=AnthropicModelSettings(
                                anthropic_cache_instructions='1h',
                                anthropic_cache_tool_definitions='1h'
                            ))
        self.amadeus_agent = Agent(model=self.model, system_prompt=amadeus_ai_personnality(), tools=[duckduckgo_search_tool()])
        
        self.message_history = []
        self.session_facts = []

        print(f"[{PLUGIN_NAME}] Amadeus plugin is now ready to use")
        chat: Chat = get_global('chat')
        
        twitch_bot: Twitch = get_global('twitch_bot') # type: ignore
        user = get_global('main_user')
        channel_info = await twitch_bot.get_channel_information(broadcaster_id=user.id) # type: ignore
        game_name = channel_info[0].game_name
        stream_title = channel_info[0].title

        result = await self.amadeus_agent.run(
            f'Amadeus, le live commence. La catégorie / le jeu est {game_name}. Miel indique que le titre de son stream est le suivant : "{stream_title}". A toi désormais d\'accueilir le chat !'
        )
        self.message_history += result.new_messages()
        self.session_facts.append(result.output)
        await self.send_twitch_message(result.output)


    @on_chat_message
    async def on_chat_message(self, message):
        await super().on_chat_message(message)
        print(f"[{PLUGIN_NAME}] Amadeus plugin received chat message: {message}")

        if self.amadeus_config.twitch_bot_username.lower() in message.user.name.lower():
            return
        
        user_summary = self.db.get_user_summary_by_id(message.user.id)

        # Regarde si le message mentionne Amadeus
        if f'@{self.amadeus_config.twitch_bot_username.lower()}' in message.text.lower():
            print(f"[{PLUGIN_NAME}] Amadeus plugin is processing the message with the agent...")

            ### Récupération des événements de stream
            session_facts = '\n'.join(self.session_facts)

            ### Message d'Amadeus
            result = await self.amadeus_agent.run(
                [
                    f'# Evenements du chat\n{session_facts}\n# Nouveau message de user_id: {message.user.id}\n# Ce que je sais de cet·te viewer\n{user_summary}# Contenu du message\n{message.text}'
                ],
                message_history=self.message_history,
                output_type=Amadeus_Output
            )

            print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output.amadeus_response}")
            print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output.amadeus_facts_to_remember}")

            ### Mise à jour des événements de stream et de l'historique des messages
            self.message_history += result.new_messages()
            self.session_facts.append(result.output.amadeus_facts_to_remember)

            ### Reformattage du texte afin de pouvoir être contenu dans 1 à N messages Twitch
            text = result.output.amadeus_response
            max_len = 485
            
            chunks = []
            while text:
                if len(text) <= max_len:
                    chunks.append(text)
                    break
                
                split_at = text.rfind(' ', max_len - 50, max_len)
                if split_at == -1 or split_at < max_len - 50:
                    split_at = max_len
                
                chunks.append(text[:split_at].strip())
                text = text[split_at:].strip()
            
            for chunk in chunks:
                if chunk:
                    await message.reply(chunk)

            # Crée un résumé des événements de stream pour ne pas surcharger le contexte
            if len(self.session_facts) > 30:
                res = await self.amadeus_agent.run(
                    f"Voici la liste des événements du stream. Crée un résumé du contenu en quelques phrases parmi ce qui semble être le plus important :\n{session_facts}"
                )
                self.session_facts = []
                self.session_facts.append(res.output)
                
                print(f'[{self.plugin_name}] Amadeus has condensed stream events into : {res.output}')


    @on_custom_message
    async def on_custom_message(self, message: CustomMessage):
        if message.from_plugin == 'streamlabs_charity':
            if message.data['type'] == 'new_donation':
                don_info = message.data
                res = await self.amadeus_agent.run(
                    f"Amadeus, nous venons de recevoir un don de {don_info['donation_amount_formatted']} de la part de {don_info['donation_from']} pour l'événement caritatif soutenant l'association des Petits Princes pour aider les enfants atteints de maladies graves à réaliser leurs rêves. Je te laisse remercier chaleureusement la personne, tout comme je le fais actuellement !"
                )
                text = res.output
                
                if don_info['donation_from_twitchname'] != '':
                    text = f"@{don_info['donation_from_twitchname']} " + text

                await self.send_twitch_message(text)

                c = CustomMessage(self.plugin_name, {'type':'get_session_donations'}, 'streamlabs_charity')
                await emit_signal('on_custom_message', c)
            if message.data['type'] == 'session_donations':
                session_donations = message.data['donations']
                res = await self.amadeus_agent.run(
                    f"Amadeus, voici la liste de tous les dons faits au cours de cette session de stream pour l'événement caritatif soutenant l'association des Petits Princes pour aider les enfants atteints de maladies graves à réaliser leurs rêves:\n{session_donations}\nJe te laisse remercier chaleureusement toutes ces personnes, avec la plus grande tendresse et joie possible."
                )
                text = res.output

                await self.send_twitch_message(text)
        
        elif message.from_plugin == 'amadeus_discord':
            if message.data['type'] == 'discord_message':
                res = await self.amadeus_agent.run(
                    message.data['content']
                )
                text = res.output
                
                c = CustomMessage(self.plugin_name,
                                  {
                                      'type': 'amadeus_discord_message',
                                      'message': message.data['message'],
                                      'content': text
                                  },
                                  'amadeus_discord')
                await emit_signal('on_custom_message', c)

    
    async def send_twitch_message(self, text):
        chat: Chat = get_global('chat')

        max_len = 485
            
        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break
            
            split_at = text.rfind(' ', max_len - 50, max_len)
            if split_at == -1 or split_at < max_len - 50:
                split_at = max_len
            
            chunks.append(text[:split_at].strip())
            text = text[split_at:].strip()
        
        for chunk in chunks:
            if chunk:
                await chat.send_message(self.amadeus_config.target_channel, chunk)


exported_class = Amadeus