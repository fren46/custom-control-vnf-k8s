import json
import os
from datetime import datetime, timedelta

#import redis
from requests import post

from base64 import b64decode

from krules_core.base_functions import RuleFunctionBase, DispatchPolicyConst
from krules_core.base_functions.misc import PyCall
from krules_core.providers import subject_factory, event_router_factory, configs_factory


class Schedule(RuleFunctionBase):

    def execute(self, message=None, subject=None, payload=None, hash=None, when=lambda _: datetime.now(), replace=False):

        if message is None:
            message = self.message
        if subject is None:
            subject = self.subject
        if payload is None:
            payload = self.payload

        if str(self.subject) != str(subject):
            subject = subject_factory(str(subject), event_info=self.subject.event_info())

        if callable(when):
            when = when(self)
        if type(when) is not str:
            when = when.isoformat()


        new_payload = {"message": message, "subject": str(subject), "payload": payload, "when": when, "replace": replace}

        event_router_factory().route("schedule-message", subject, new_payload,
                                       dispatch_policy=DispatchPolicyConst.DIRECT)


class WebsocketNotificationEventClass(object):

    CHEERING = "cheering"
    WARNING = "warning"
    CRITICAL = "critical"
    NORMAL = "normal"


# class WebsocketDevicePublishMessage(RuleFunctionBase):
#
#     def execute(self, _payload):
#
#         r = redis.StrictRedis.from_url(os.environ['REDIS_PUBSUB_ADDRESS'])
#         r.publish(os.environ['WEBSOCKET_DEVICES_NOTIFICATION_RKEY'], json.dumps(
#             {
#                 "device": self.subject.name,
#                 "payload": _payload
#             }
#         ))


class SlackPublishMessage(PyCall):

    def execute(self, channel=None, text="", *args, **kwargs):
        channel = channel or "devices_channel"
        slack_settings = configs_factory().get("apps").get("slack")
        #funzione execute della classe PyCall, non fa altro che eseguire una generica funzione python
        #la funzione viene eseguita all'interno di un try catch
        #la funzione che esegue è quella passata come primo argomento
        super().execute(post, args=(slack_settings[channel],), kwargs={
            "json": {
                "type": "mrkdwn",
                "text": text
            }
        })

class SlackPublishInteractiveMessage(PyCall):

    def execute(self, channel=None, text="", *args, **kwargs):
        channel = channel or "devices_channel"
        slack_settings = configs_factory().get("apps").get("slack")
        super().execute(post, args=(slack_settings[channel],), kwargs={
            "json": {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": text
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Accetto"
                                    #"emoji": "true"
                                },
                                "value": self.subject.name
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Rifiuta"
                                    #"emoji": "true"
                                },
                                "value": "click_false"
                            }
                        ]
                    }
                ]
            }
        })

class B64Decode(RuleFunctionBase):

    def execute(self, source, payload_dest):
        self.payload[payload_dest] = json.loads(b64decode(source).decode("utf-8"))

class PPrint(RuleFunctionBase):

    def execute(self, something):
        from pprint import pprint
        pprint(something)
