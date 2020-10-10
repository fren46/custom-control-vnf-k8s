from flask import Flask, request, jsonify
import json, logging
from cloudevents.http import CloudEvent, to_structured
import requests
#from kubernetes import client
app = Flask(__name__)

@app.route("/")
def hello():
    logging.info("Hello World from Flask")
    return "Hello world"

@app.route("/", methods=['POST'])
def button_response():

    payload = json.loads(request.form.get("payload"))
    print("payload: ", payload)
    print("utente che ha fatto la scelta: ", payload["user"]["name"])
    print("azione cliccata: ", payload["actions"][0]["value"])
    if payload["actions"][0]["value"] == "click_false":
        print("non mandare un niente perchè ha rifiutato")
    else:
        #creo un evento cloudEvent
        attributes = {
            "type": "new-firewall-approved",
            #"source": "python_webserver",
            "subject": payload["actions"][0]["value"]
        }
        data = {"message": "L'utente ha accettato"}
        event = CloudEvent(attributes, data)
        # Creazione della richiesta HTTP rappresentante di un evento CloudEvent con contenuto strutturato
        headers, body = to_structured(event)
        # POST
        requests.post("http://broker-ingress.knative-eventing.svc.cluster.local/default/default", data=body, headers=headers)
        print("post mandata")
    return "tutto ok"

    # logging.info("\nusername: ", request.form['user'].username)
    # logging.info("\naction type: ", request.form['actions'][0].type)
    # logging.info("\nvalue of action: ", request.form['actions'][0].value)
    # return request.form['actions'][0].value



if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)
