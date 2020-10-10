from krules_core.base_functions import *

from krules_core import RuleConst as Const

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
#     on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_errors,
)


class SetMultusInterfaces(RuleFunctionBase):

    def execute(self):
        '''
        take the list of networks interfaces name set by multus in "k8s.v1.cni.cncf.io/networks"
        annotation and for each name add into the subject the pair name-status, which status is
        the status set by multus in "k8s.v1.cni.cncf.io/networks-status" annotation.
        (status mainly contain the ip of the network interface)
        :return:
        '''
        interfaces = self.payload["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks"]
        statuses = self.payload["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks-status"]
        statuses = json.loads(statuses)
        interfaces = interfaces.split(', ')
        for interface in interfaces:
            for status in statuses:
                if status.get("name") == interface:
                    #self.payload[status["interface"]] = status["ips"][0]
                    self.subject.set(status.pop("name"), status)
                    break


rulesdata = [

    """
    filter resources with multus network annotations
    set annotations properties with interfaces name and IPs 
    set extended property of resources
    """,
    {
        rulename: "multus-resources-identifier",
        subscribe_to: ["k8s.resource.add", "k8s.resource.update", "k8s.resource.detector"],
        ruledata: {
            filters: [
                IsTrue(lambda payload:
                       "k8s.v1.cni.cncf.io/networks" in payload.get("metadata").get("annotations", {}) and
                       "k8s.v1.cni.cncf.io/networks-status" in payload.get("metadata").get("annotations", {})),
            ],
            processing: [
                SetMultusInterfaces(),
                SetSubjectExtendedProperty("multusapp",
                                           lambda payload: payload.get("metadata").get("labels", {}).get("app", "unknown"))
            ],
        },
    },

    """
    filter deletion of resources with multus network annotations
    generate an event with type "startup" which reconfigure the entire network
    """,
    {
        rulename: "multus-resources-deletion-identifier",
        subscribe_to: ["k8s.resource.delete"],
        ruledata: {
            filters: [
                IsTrue(lambda payload:
                       "k8s.v1.cni.cncf.io/networks" in payload.get("metadata").get("annotations", {}) and
                       "k8s.v1.cni.cncf.io/networks-status" in payload.get("metadata").get("annotations", {})),
            ],
            processing: [
                Route(type="startup", dispatch_policy=DispatchPolicyConst.DIRECT)
            ],
        },
    },
]
