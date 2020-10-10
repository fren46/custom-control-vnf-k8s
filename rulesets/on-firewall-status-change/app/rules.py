from krules_core.base_functions import *
import json
from krules_core import RuleConst as Const
from app_functions.k8s import K8sObjectsQuery, exec_command, k8s_subject

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory, subject_factory
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


def add_fw_to_lb(ob, dest_net_subnet, fw_ips):
    '''
    modify the routing table of the pod passed as first parameter using the
    destination network "dest_net_subnet" and the IPs of the FW "fw_ips".
    :param ob: multipath-router get by K8sObjectQuery
    :param dest_net_subnet: ip with subnetmask of the destination network
    :param fw_ips: list of the approved FW
    :return: None
    '''
    command = [
        '/bin/sh',
        '-c',
        'ip route del '+dest_net_subnet]
    exec_command(ob, command=command, container="multipath", preload_content=False)
    if len(fw_ips):
        separator = ' via '
        if len(fw_ips) > 1:
            separator = ' nexthop via '
        command = [
            '/bin/sh',
            '-c',
            'ip route add '+dest_net_subnet+separator+separator.join(fw_ips)]
        exec_command(ob, command=command, container="multipath", preload_content=False)


def set_subnet_in_payload(obj, name, payload):
    '''
    if the NetworkAttachmentDefinition passed as parameter has the same name of the one
    passed as second parameter, it's added the network IP to payload
    :param obj: NetworkAttachmentDefinition get by the K8sObjectsQuery
    :param name: the name of the subnet that interest us
    :param payload: payload of the context firewall
    :return: None
    '''
    if obj["metadata"]["name"] == name:
        payload["subnet"] = json.loads(obj["spec"]["config"])["ipam"]["subnet"]


def set_running_fw_in_payload(obj, payload):
    '''
    if the FW passed as parameter is approved, it's added the FW IP to payload
    :param obj: firewall get by the K8sObjectsQuery
    :param payload: payload of the context firewall
    :return: None
    '''
    subject = k8s_subject(obj)
    try:
        if subject.get("approval_status") == "approved":
            payload["fw_ips"] = payload.get("fw_ips", [])
            payload["fw_ips"].append(subject.get(LB_FW_NETWORK)["ips"][0])
    except AttributeError as ex:
        print(str(ex))


rulesdata = [

    """
    on property approval_status of subject change to approved: 
    it's retrieved the IP network from the NetworkAttachmentDefinition 
    and it's reconfigured the routing table of the multipath-routing resource 
    """,
    {
        rulename: "on-firewall-approved",
        subscribe_to: "subject-property-changed",
        ruledata: {
            filters: [
                SubjectPropertyChanged("approval_status", "approved"),
            ],
            processing: [
                K8sObjectsQuery(
                    apiversion="k8s.cni.cncf.io/v1",
                    kind="NetworkAttachmentDefinition",
                    foreach=lambda payload: lambda obj:
                        set_subnet_in_payload(obj.obj, "fw-sv-macvlan-conf", payload),
                ),
                K8sObjectsQuery(
                    apiversion="v1",
                    kind="Pod",
                    filters={
                        "selector": {
                            "app": "firewall",
                        },
                    },
                    foreach=lambda payload: lambda obj:
                        set_running_fw_in_payload(obj.obj, payload)
                ),
                K8sObjectsQuery(
                    apiversion="v1",
                    kind="Pod",
                    filters={
                        "selector": {
                            "app": "multipath",
                        },
                    },
                    foreach=lambda payload: lambda obj: (
                            add_fw_to_lb(obj,
                                     payload["subnet"],
                                     payload["fw_ips"])
                    )
                )
            ],
        },
    },

]
