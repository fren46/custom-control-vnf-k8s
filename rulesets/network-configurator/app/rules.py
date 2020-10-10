from krules_core.base_functions import *

from krules_core import RuleConst as Const

from app_functions.k8s import K8sObjectsQuery, exec_command, k8s_subject

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory, event_router_factory
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

CL_LB_NETWORK = "cl-lb-macvlan-conf"
LB_FW_NETWORK = "lb-fw-macvlan-conf"
FW_SV_NETWORK = "fw-sv-macvlan-conf"


class PPrint(RuleFunctionBase):

    def execute(self, something):
        from pprint import pprint
        pprint(something)


def set_multus_resources(obj, payload):
    app = obj.obj.get("metadata").get("labels", {}).get("app")
    if app is not None:
        event_router_factory().route("k8s.resource.detector",
                                     "k8s:{}".format(obj.obj["metadata"]["selfLink"]),
                                     obj.obj,
                                     dispatch_policy=DispatchPolicyConst.DIRECT)
        payload[app] = payload.get(app, [])
        payload[app].append(obj)


def set_subnet_in_payload(obj, payload):
    payload[obj["metadata"]["name"]] = json.loads(obj["spec"]["config"])["ipam"]["subnet"]


class ConfigNetworkFunction(RuleFunctionBase):

    def execute(self, resources, container, dest_subnet, nexthops, source_net):
        '''

        :param resources:
        :param dest_subnet: indirizzo ip della rete di destinazione
        :param container:
        :param nexthops:
        :param source_net: nome della rete di partenza
        :return:
        '''
        command = [
            '/bin/sh',
            '-c',
            'ip route del ' + dest_subnet] #self.payload[FW_SV_NETWORK]
        for res in resources: #self.payload["client"]
            exec_command(res, command=command, container=container, preload_content=False)
        ips = []
        for nexthop in nexthops: #self.payload["multipath"]
            statuses = json.loads(nexthop.obj["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks-status"])
            ips.append(get_interface_ip(source_net, statuses)) #CL_LB_NETWORK
        if len(ips):
            separator = ' via '
            if len(ips) > 1:
                separator = ' nexthop via '
            command = [
                '/bin/sh',
                '-c',
                'ip route add ' + dest_subnet + separator + separator.join(ips)]
            for res in resources:
                exec_command(res, command=command, container=container, preload_content=False)


def get_interface_ip(interface, statuses):

    for status in statuses:
        if status.get("name") == interface:
            return status["ips"][0]


class SetApprovalStatus(RuleFunctionBase):

    def execute(self, firewalls):
        for firewall in firewalls:
            subject = k8s_subject(firewall.obj)
            if "approval_status" not in subject or subject.approval_status == "approved":
                subject.set("approval_status", None)
                subject.set("approval_status", "approved")


rulesdata = [

    """
    
    """,
    {
        rulename: "network-configurator",
        subscribe_to: "startup",
        ruledata: {
            filters: [
            ],
            processing: [
                K8sObjectsQuery(
                    apiversion="v1",
                    kind="Pod",
                    foreach=lambda payload: lambda obj: set_multus_resources(obj, payload)
                ),
                K8sObjectsQuery(
                    apiversion="k8s.cni.cncf.io/v1",
                    kind="NetworkAttachmentDefinition",
                    foreach=lambda payload: lambda obj:
                    set_subnet_in_payload(obj.obj, payload),
                ),
                # configurazione client
                ConfigNetworkFunction(
                    resources=lambda payload: payload["client"],
                    container="client",
                    dest_subnet=lambda payload: payload[FW_SV_NETWORK],
                    nexthops=lambda payload: payload["multipath"],
                    source_net=CL_LB_NETWORK
                ),
                # configurazione multipath routing
                # ConfigNetworkFunction(
                #     resources=lambda payload: payload["multipath"],
                #     container="multipath",
                #     dest_subnet=lambda payload: payload[FW_SV_NETWORK],
                #     nexthops=lambda payload: payload["firewall"],
                #     source_net=LB_FW_NETWORK
                # ),
                SetApprovalStatus(lambda payload: payload["firewall"]),
                # configurazione firewall
                ConfigNetworkFunction(
                    resources=lambda payload: payload["firewall"],
                    container="firewall-sample",
                    dest_subnet=lambda payload: payload[CL_LB_NETWORK],
                    nexthops=lambda payload: payload["multipath"],
                    source_net=LB_FW_NETWORK
                ),
                # configurazione web server
                ConfigNetworkFunction(
                    resources=lambda payload: payload["server"],
                    container="node-server",
                    dest_subnet=lambda payload: payload[CL_LB_NETWORK],
                    nexthops=lambda payload: payload["firewall"],
                    source_net=FW_SV_NETWORK
                ),
            ],
        },
    },

]
