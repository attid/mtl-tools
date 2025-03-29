import httpx
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import OpenAI, ChatOpenAI
from langchain_core.tools import tool
from loguru import logger

from other.config_reader import config


class LangChainManager:
    def __init__(self, tools: list = []):
        self.openai_key = config.openai_key
        self.ids = []
        self.tools = tools
        self.debug = False

        self.checkpointer = MemorySaver()

        def on_response(response: httpx.Response):
            try:
                response.read()
                data = response.json()
                gen_id = data.get("id")
                if gen_id:
                    # print("Полученный gen id:", gen_id)
                    self.ids.append(gen_id)
            except Exception as e:
                print("Не удалось обработать JSON:", e)

        self.httpx_client = httpx.Client(event_hooks={"response": [on_response]})

        self.model = ChatOpenAI(
            # model="openai/gpt-4o-mini", #99
            # model="openai/gpt-4o", #1682
            # model="google/gemini-2.0-flash-001", #42
            model="anthropic/claude-3-haiku", #876
            # model="cohere/command-r", #100
            # model="meta-llama/llama-3.1-70b-instruct", #72
            # model="cohere/command-r-plus", #653
            # model="google/gemini-flash-1.5-8b", #17

            api_key=config.openai_key,
            base_url="https://openrouter.ai/api/v1",
            http_client=self.httpx_client,

            temperature=0
        )
        self.llm_graph = create_react_agent(self.model, tools, checkpointer=self.checkpointer)

    def calc_costs(self):
        total_cost = 0
        for id_ in self.ids:
            response = self.httpx_client.get(
                "https://openrouter.ai/api/v1/generation",
                headers={"Authorization": f"Bearer {config.openai_key.get_secret_value()}"},
                params={"id": id_}
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                total_cost += data.get("total_cost", 0)

        # Format the total cost with 6 decimal places
        return "{:.6f}".format(total_cost)

    def invoke(self, text):
        response  = self.llm_graph.invoke(
            {"messages": [{"role": "user", "content": text}]},
             config={"configurable": {"thread_id": 42}}
        )

        return response["messages"][-1].content

    def stream(self, text):
        return_message = ""

        for event in self.llm_graph.stream({"messages": ("user", text)},
                                           config={"configurable": {"thread_id": 42}}):
            #  print(1, event)
            for value in event.values():
                return_message = value["messages"][-1].content
                if self.debug:
                    logger.debug(return_message)
                # print("Assistant:", value["messages"][-1].content)

        #print(f"Затраты на вызов: {calc_costs()}")
        return return_message

