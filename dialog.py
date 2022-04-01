import os
from google.cloud import dialogflow

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "mtl-skynet-talks.json"

# https://dialogflow.cloud.google.com/#/editAgent/mtl-skynet-hldy/

def talk(session_id, msg):
    project_id = 'mtl-skynet-hldy'
    language_code = 'RU'

    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    #print("Session path: {}\n".format(session))


    text_input = dialogflow.TextInput(text=msg[:240], language_code='RU')
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )

    if len(response.query_result.fulfillment_text) > 2:
        return response.query_result.fulfillment_text
    else:
        return "Žao mi je, što ne razumijem."

    #print("=" * 20)
    #print("Query text: {}".format(response.query_result.query_text))
    #print(
    #     "Detected intent: {} (confidence: {})\n".format(
    #        response.query_result.intent.display_name,
    #        response.query_result.intent_detection_confidence,
    #    )
    #)
    #    print("Fulfillment text: {}\n".format(response.query_result.fulfillment_text))


#def talk(id,msg):

if __name__ == "__main__":
    pass
    print(talk(9,'Как дела'))