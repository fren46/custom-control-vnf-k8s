from krules_core.base_functions import *
import json
from krules_core import RuleConst as Const

from app_functions import SlackPublishInteractiveMessage

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all, publish_proc_events_filtered

# import pprint
# proc_events_rx_factory().subscribe(
#     on_next=pprint.pprint
# )
# proc_events_rx_factory().subscribe(
#     on_next=publish_results_all,
# )
proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_errors,
)


class PPrint(RuleFunctionBase):

    def execute(self, something):
        from pprint import pprint
        pprint(something)


class ComposeText(RuleFunctionBase):

    def execute(self, payload_dest):
        '''
        compose the text that will be show on the slack message
        :param payload_dest: name of payload property where the text will be memorized
        :return: None
        '''
        self.payload[payload_dest]="E' stato creata la risorsa \"{}\" con nome \"{}\" nel namespace \"{}\". " \
                                   "Si desidera bilanciare il carico anche su quest'ultima risorsa?".format(
            self.payload['_event_info']['multusapp'],
            self.payload['_event_info']['name'],
            self.payload['_event_info']['namespace']
        )
        # self.payload[payload_dest]=":{}: *{}:event:{}:{}*\n from: {}\nregarding: {}\n```{}```".format(
        #     self.payload["icon"],
        #     self.payload['k8s_event_info']['namespace'],
        #     self.payload["reason"],
        #     self.subject.event_info()['type'].split(".")[-1],
        #     self.payload["source"]["component"],
        #     "{}:{}:{}".format(
        #         self.payload["involvedObject"]["apiVersion"],
        #         self.payload["involvedObject"]["kind"],
        #         self.payload["involvedObject"]["name"]
        #     ),
        #     self.payload.get('message'))


rulesdata = [

    """
    Intercept FW creation and check if phase is "Running" and 
    if approval_status property is not in the subject
    """,
    {
        rulename: "intercept-fw-creation",
        subscribe_to: [
            "k8s.resource.add",
            "k8s.resource.update"
        ],
        ruledata: {
            filters: [
                IsTrue(lambda payload:
                       payload.get("status", {}).get("phase", "") == "Running"),
                IsTrue(lambda subject: "approval_status" not in subject),
            ],
            processing: [
                PPrint("#############  Subject   ##############"),
                PPrint(lambda subject: subject),
                PPrint("#############  Payload   ##############"),
                PPrint(lambda payload: payload),
                SetSubjectProperty("approval_status", "pending"),
                ComposeText("text"),
                SlackPublishInteractiveMessage(
                    channel="kr-k8s-lab-clusterevents",
                    text=lambda payload: payload["text"]
                    )
            ],
        },
    },

    """
    on firewall confirm event from web server
    it changes the value of property approval_status into approved
    """,
    {
        rulename: "new-firewall-approved-subscriber",
        subscribe_to: "new-firewall-approved",
        ruledata: {
            filters: [
                # TODO: capire come mai anche se la condizione nel filtro è vera gli eventi non lo superano
                # IsTrue(lambda subject: "approval_status" in subject and subject.approval_status == "pending")
            ],
            processing: [
                # Come la SetSubjectProperty ma non usa la cache, la modifica viene fatta
                # subito senza aspettare la fine della regola
                StoreSubjectProperty("approval_status", "approved"),
            ],
        },
    },

]
