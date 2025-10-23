import os
from typing import Dict
import openai
from pydantic import BaseModel


class Registry(BaseModel):
    """Registry for storing and building classes."""

    name: str
    entries: Dict = {}
    translator_entries: Dict = {} 

    def register(self, keys: list):
        def decorator(cls):
            for key in keys:
                if key in self.entries:
                    raise ValueError(f"Key {key} is already registered with a different class.")
                self.entries[key] = cls
            return cls
        return decorator


    def build(self, type: str, **kwargs):
        if type not in self.entries:
            raise ValueError(
                f'{type} is not registered. Please register with the .register("{type}") method provided in {self.name} registry'
            )
        agent_params = {}

        # 支持所有OpenAI API格式的模型（GPT、Qwen等）
        if "gpt" in type.lower() or "o1" in type.lower() or "qwen" in type.lower():      
            # 支持自定义OpenAI API端点
            if "base_url" in kwargs and "api_key" in kwargs:
                # 使用自定义端点
                client = openai.OpenAI(
                    api_key=kwargs["api_key"],
                    base_url=kwargs["base_url"]
                )
            else:
                # 使用Azure OpenAI（原有逻辑）
                try:
                    azure_endpoint = os.environ['AZURE_OPENAI_API_BASE']
                except KeyError:
                    raise EnvironmentError("Environment variable AZURE_OPENAI_API_BASE is not set.")
                try:
                    api_version = os.environ['AZURE_OPENAI_API_VERSION']
                except KeyError:
                    raise EnvironmentError("Environment variable AZURE_OPENAI_API_VERSION is not set.")
                try:
                    api_key = os.environ['AZURE_OPENAI_API_KEY']
                except KeyError:
                    raise EnvironmentError("Environment variable AZURE_OPENAI_API_KEY is not set.")
                client = openai.AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_version=api_version,
                    api_key=api_key
                )
            agent_params = {
                "client": client,
                "tokenizer": None,
                "llm": kwargs["llm"],
                "temperature": kwargs["temperature"]
            }
        elif 'human' in type.lower():
            agent_params = {
                "client": None,
                "tokenizer": None,
                "llm": None,
                "temperature": 0
            }
        return type, agent_params

    def build_agent(self, type: str,
                    player_idx,
                    agent_param,
                    env_param,
                    log_file):
        
        if type not in self.entries:
            raise ValueError(
                f'{type} is not registered. Please register with the .register("{type}") method provided in {self.name} registry'
            )
        return self.entries[type](client=agent_param["client"],
                                    tokenizer=agent_param["tokenizer"],
                                    llm=agent_param["llm"],
                                    temperature=agent_param["temperature"],
                                    log_file=log_file)

    def get_all_entries(self):
        return self.entries
