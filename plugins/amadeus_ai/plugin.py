from models.amadeus_plugin import AmadeusPlugin
from models.decorators import on_follow, on_load, on_chat_message
from models.globals import set_global, get_global
from config.amadeus_config import Amadeus_Config
from twitchAPI.chat import Chat

PLUGIN_NAME = "amadeus_ai"

class Amadeus(AmadeusPlugin):
    

    plugin_name = PLUGIN_NAME


    def __init__(self) -> None:
        super().__init__()

        self.config_parser.set(self.plugin_name, 'anthropic_secret', '')

        self.write_config(overwrite=False)
        self.read_config()

    @on_load
    async def on_load(self) -> None:
        await super().on_load()

        from pydantic_ai import Agent
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
        self.amadeus_agent = Agent(model=self.model, system_prompt=self.amadeus_config.amadeus_ai_personnality(), tools=[duckduckgo_search_tool()])
        self.message_history = []

        print(f"[{PLUGIN_NAME}] Amadeus plugin is now ready to use")
        chat: Chat = get_global('chat')
        await chat.send_message(self.amadeus_config.target_channel, "Bonjour tout le monde !")


    @on_chat_message
    async def on_chat_message(self, message):
        await super().on_chat_message(message)
        print(f"[{PLUGIN_NAME}] Amadeus plugin received chat message: {message}")

        if self.amadeus_config.twitch_bot_username.lower() in message.user.name.lower():
            return

        # Regarde si le message mentionne Amadeus
        if f'@{self.amadeus_config.twitch_bot_username.lower()}' in message.text.lower():
            print(f"[{PLUGIN_NAME}] Amadeus plugin is processing the message with the agent...")
            result = await self.amadeus_agent.run(
                [
                    f'# Message provenant de {message.user.name}\n{message.text}'
                ],
                message_history=self.message_history
            )

            print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output}")

            self.message_history += result.new_messages()

            text = result.output
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


exported_class = Amadeus