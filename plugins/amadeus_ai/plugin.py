from typing import List

from models.amadeus_plugin import AmadeusPlugin
from models.decorators import on_follow, on_load, on_chat_message
from models.globals import set_global, get_global
from config.amadeus_config import Amadeus_Config
from twitchAPI.chat import Chat

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

        self.db = Amadeus_DB(self.plugin_name, self.config_parser)


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
        self.find_user_agent = Agent(model=self.model,
                                     system_prompt="""
                                     You are an agent whose purpose is to find possible usernames in a message.
                                     When usernames are found, you must call the `get_twitch_user_and_info` tool on them.
                                     - If no username is found in the message, stop.
                                     """,
                                     output_type=Amadeus_FindUser)
        
        self.message_history = []
        self.session_facts = []

        print(f"[{PLUGIN_NAME}] Amadeus plugin is now ready to use")
        chat: Chat = get_global('chat')
        await chat.send_message(self.amadeus_config.target_channel, "Bonjour tout le monde !")

        
        @self.find_user_agent.tool_plain
        def get_twitch_user_and_info(username: str):
            """_summary_
                Allows me to know if a viewer is known on this stream and if so, gets a summary of my interactions with them
            Returns:
                string: summary of the conversation with the viewer
            """
            return self.db.get_user_summary_by_username(username)


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

            ### Récupération des informations sur les viewers potentiellement cités dans le message
            result = await self.find_user_agent.run(
                message.text
            )
            print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output.users_sumarries}")
            users_summaries = ""
            if len(result.output.users_sumarries) > 0:
                users_summaries = "# Éléments connus sur les viewers cités:\n"
                for summary in result.output.users_sumarries:
                    if 'amadeus_mk1' not in summary.lower():
                        users_summaries += summary + '\n'
            print(users_summaries)
            ### Récupération des événements de stream
            session_facts = '\n'.join(self.session_facts)

            ### Message d'Amadeus
            result = await self.amadeus_agent.run(
                [
                    f'# Evenements du chat\n{session_facts}\n# Nouveau message de {message.user.name}\n# Ce que je sais de cet·te viewer\n{user_summary}\n{users_summaries}# Contenu du message\n{message.text}'
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


exported_class = Amadeus