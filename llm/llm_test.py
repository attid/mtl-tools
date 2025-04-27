from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from llm.llm_main import LangChainManager
from other.config_reader import config

import httpx

def on_response(response: httpx.Response):
    try:
        # Принудительно считываем содержимое, чтобы отключить режим стриминга.
        response.read()
        data = response.json()
        gen_id = data.get("id")
        if gen_id:
            #print("Полученный gen id:", gen_id)
            ids.append(gen_id)
    except Exception as e:
        print("Не удалось обработать JSON:", e)

# Создаем клиент с хуком для ответа
client = httpx.Client(event_hooks={"response": [on_response]})


tools = [get_user_location, get_weather_in_city]

model = ChatOpenAI(
    # model="openai/gpt-4o-mini", #99
    # model="openai/gpt-4o", #1682
    # model="google/gemini-2.0-flash-001", #42
    # model="anthropic/claude-3-haiku", #876
    # model="cohere/command-r", #100
    # model="meta-llama/llama-3.1-70b-instruct", #72
    # model="cohere/command-r-plus", #653
    # model="google/gemini-flash-1.5-8b", #17

    api_key=config.openai_key,
    base_url="https://openrouter.ai/api/v1",
    http_client=client,
    temperature=0
)

# Initialize memory to persist state between graph runs
checkpointer = MemorySaver()

app = create_react_agent(model, tools)

text = "привет как дела? а как там погода в моем городе?"
# # Use the agent
# final_state = app.invoke(
#     {"messages": [{"role": "user", "content": text}]}
# )
#
# print(final_state["messages"][-1].content)


# while True:
#
#     user_input = input("User: ")
#     if user_input.lower() in ["quit", "exit", "q"]:
#         print("Goodbye!")
#
#         break

return_message = ""

for event in app.stream({"messages": ("user", text)}):
    #  print(1, event)
    for value in event.values():
        return_message = value["messages"][-1].content
        #print("Assistant:", value["messages"][-1].content)


print(return_message)
print(f"Затраты на вызов: {calc_costs()}")

if __name__ == "__main__":
    tools = []
    llm = LangChainManager()