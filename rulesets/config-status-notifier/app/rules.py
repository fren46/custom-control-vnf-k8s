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


class PPrint(RuleFunctionBase):

    def execute(self, something):
        from pprint import pprint
        pprint(something)


rulesdata = [

    """
    filter the update of the "network-configurator" rulesset and when it is Running
    an event with type "startup" is generated. This event configure the entire network.
    """,
    {
        rulename: "on-net-config-status-change",
        subscribe_to: "k8s.resource.update",
        ruledata: {
            filters: [
                IsTrue(lambda payload: payload.get("metadata").get("labels", {}).get(
                          "airspot.krules.dev/ruleset") == "network-configurator"),
                IsTrue(lambda payload:
                      payload.get("status", {}).get("phase", "") == "Running"),
            ],
            processing: [
                Route(type="startup", dispatch_policy=DispatchPolicyConst.DIRECT)
            ],
        },
    },

]
