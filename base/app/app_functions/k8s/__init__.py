from urllib.parse import urlencode

import pykube
from krules_core.base_functions import RuleFunctionBase
import websocket
import ssl
import six
import posixpath


# class InitK8sClient(RuleFunctionBase):
#
#     def execute(self, payload_dest="k8s_client"):
#         config = pykube.KubeConfig.from_service_account()
#         api = pykube.HTTPClient(config)
#
#         self.payload["k8s_client"] = api
#
#         return api
from krules_core.providers import subject_factory


def k8s_subject(obj):
    return subject_factory("k8s:{}".format(obj["metadata"]["selfLink"]), event_data=obj)


class K8sObjectsQuery(RuleFunctionBase):
    def execute(self, apiversion=None, kind=None, filters={}, foreach=None, returns=None):
        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_service_account()
            api = pykube.HTTPClient(config)
            self.payload["_k8s_api_client"] = api
        use_context = apiversion is None and kind is None and len(filters) == 0
        context = self.payload
        if use_context and context.get("metadata", {}).get("name") is None:
            resp = api.session.get(url=f"{api.url}{self.subject.name[len('k8s:'):]}")
            resp.raise_for_status()
            context = resp.json()
        if use_context:
            apiversion = context["apiversione"]
            kind = context["kind"]
        obj = pykube.object_factory(api, apiversion, kind)
        if "namespace" not in filters:
            filters.update({
                "namespace": self.subject.get_ext("namespace")
            })
        qobjs = obj.objects(api).filter(**filters)
        if foreach is not None:
            for obj in qobjs:
                foreach(obj)
        if returns is not None:
            return returns(qobjs)
        return len(qobjs)


class K8sObjectUpdate(RuleFunctionBase):
    def execute(self, func, subresource=None, name=None, apiversion=None, kind=None, filters={}):
        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_service_account()
            api = pykube.HTTPClient(config)
            self.payload["_k8s_api_client"] = api
        use_context = subresource is None and name is None and apiversion is None and kind is None and len(filters) == 0
        context = self.payload
        if use_context and context.get("metadata", {}).get("name") is None:
            resp = api.session.get(url=f"{api.url}{self.subject.name[len('k8s:'):]}")
            resp.raise_for_status()
            context = resp.json()
        if use_context:
            apiversion = context["apiVersion"]
            kind = context["kind"]
            name = context["metadata"]["name"]
        #     namespace = context["metadata"]["namespace"]
        # else:
        #     namespace = self.subject.get_ext("namespace")
        factory = pykube.object_factory(api, apiversion, kind)
        # if "namespace" not in filters:
        #     filters.update({
        #         "namespace": self.subject.get_ext("namespace")
        #     })
        # obj.update() might fail if the resource was modified between loading and updating. In this case you need to retry.
        # Reference: https://pykube.readthedocs.io/en/latest/howtos/update-deployment-image.html
        while True:
            obj = factory.objects(api).filter(**filters).get(name=name)
            func(obj.obj)
            try:
                obj.update(subresource=subresource)
                break
            except pykube.exceptions.HTTPError as ex:
                print(str(ex))
                if ex.code == 409:
                    continue
                else:
                    raise ex



# class K8sObjectGet(RuleFunctionBase):
#
#     def execute(self, name=None, apiversion=None, kind=None, filter={}, returns=None, payload_dest=None, k8s_client=None, k8s_client_from="k8s_client"):
#         api = k8s_client
#         if api is None:
#             api = self.payload.get(k8s_client_from)
#         if api is None:
#             config = pykube.KubeConfig.from_service_account()
#             api = pykube.HTTPClient(config)
#             self.payload["k8s_client"] = api
#
#         if apiversion is None:
#             apiversion = self.subject.get_ext("apiversion")
#         if kind is None:
#             kind = self.subject.get_ext("kind")
#         obj = pykube.object_factory(api, apiversion, kind)
#         if "namespace" not in filter:
#             filter.update({
#                 "namespace": self.subject.get_ext("namespace")
#             })
#         qobjs = obj.objects(api).filter(**filter)
#         if name is None:
#             name = self.subject.name.split("/")[-1]
#         obj = qobjs.get(name=name)
#         if payload_dest is not None:
#             self.payload[payload_dest] = obj
#
#         if returns is not None:
#             return returns(self, obj)
#
#         return obj

class K8sObjectCreate(RuleFunctionBase):

    def execute(self, obj):

        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_service_account()
            api = pykube.HTTPClient(config)
            self.payload["_k8s_api_client"] = api

        apiversion = obj.get("apiVersion")
        kind = obj.get("kind")
        pykube.object_factory(api, apiversion, kind)(api, obj).create()


def fk_err(ws, err):
    print(err)

def fk_close(ws):
    pass

def fk_message(ws, msg):
    print(msg)

class WSClient(object):

    def get_kwargs(self, **kwargs):
        """
        Creates a full URL to request based on arguments.
        :Parametes:
           - `kwargs`: All keyword arguments to build a kubernetes API endpoint
        """
        url = ""
        version = kwargs.pop("version", "v1")
        if version == "v1":
            base = kwargs.pop("base", "/api")
        elif "/" in version:
            base = kwargs.pop("base", "/apis")
        else:
            if "base" not in kwargs:
                raise TypeError("unknown API version; base kwarg must be specified.")
            base = kwargs.pop("base")
        bits = [base, version]
        # Overwrite (default) namespace from context if it was set
        if "namespace" in kwargs:
            n = kwargs.pop("namespace")
            if n is not None:
                if n:
                    namespace = n
                else:
                    namespace = self.config.namespace
                if namespace:
                    bits.extend([
                        "namespaces",
                        namespace,
                    ])
        url = kwargs.get("url", "")
        if url.startswith("/"):
            url = url[1:]
        bits.append(url)
        kwargs["url"] = self.url + posixpath.join(*bits)
        return kwargs


    """
    Websocket Client for interfacing with the Kubernetes API.
    """

    def __init__(self, **kwargs):

        self.url = kwargs['url']
        self.url = self.url.replace('http://', 'ws://')
        self.url = self.url.replace('https://', 'wss://')

        self.session = kwargs['session']
        self.token = kwargs['token']
        self.trace = kwargs['trace'] if "trace" in kwargs else False
        self.messages = []
        self.errors = []

        # Trace when enabled:
        websocket.enableTrace(self.trace)

        # Get token from session headers:
        header = None
        if 'Authorization' in self.session.headers:
            header = "Authorization: " + self.session.headers['Authorization']
        elif self.token is not None:
            header = "Authorization: %s %s" % ("Bearer", self.token)
        print("connecting to %s..." % self.url)
        self.ws = websocket.WebSocketApp(self.url,
                                    on_message=fk_message,#self.on_message,
                                    on_error=fk_err,#self.on_error,
                                    on_close=fk_close,#self.on_close,
                                    header=[header]
                                    )
        print("App created")
        #TODO revisit if ws should be a property
        #when we init http; we will trigger an invalid ws connection
        #to self.config.cluster["server"] via WSClient init and on_open
        # Check for valid ws url connections
        # Prevents errors on init with short url
        if "exec" in self.url:
            print("exec found")
            self.ws.on_open = self.on_open
            ssl_opts = {'cert_reqs': ssl.CERT_NONE}
            self.ws.run_forever(sslopt=ssl_opts)
        else:
            pass


    def on_message(self, ws, message):
        print(message)
        if message[0] == '\x01':
            message = message[1:]
        if message:
            if six.PY3 and isinstance(message, six.binary_type):
                message = message.decode('utf-8')
            self.messages.append(message)

    def on_error(self, ws, error):
        self.errors.append(error)

    def on_close(self, ws):
        pass

    def on_open(self, ws):
        pass

    def get(self, *args, **kwargs):

        client = WSClient(session=self.session, token=self.token, **self.get_kwargs(**kwargs))
        if client.errors:
            raise Exception('\n'.join([str(error) for error in client.errors]))
        return client.messages


def exec_command(pod, stdin=False, stdout=True, stderr=True, tty=False, container=None, command=None,
            preload_content=True, trace=False):
    execute_call = "exec"
    params = {"stdin": stdin, "stdout": stdout, "stderr": stderr, "tty": tty, "_preload_content": preload_content}

    if container is not None:
        params["container"] = container

    # Handle command parameter outside of urlencode:
    expand_cmds = ''
    if command is not None:
        if isinstance(command, list):
            for cmd in command:
                expand_cmds += "&" + urlencode({"command": cmd})
        else:
            # TODO review string command expansion:
            expand_cmds = "&command=%s&" % command.strip().replace(" ", "&command=")

    query_string = urlencode(params) + expand_cmds
    execute_call += "?{}".format(query_string) if query_string else ""
    kwargs = {
        "version": pod.version,
        "namespace": pod.namespace,
        "operation": execute_call,
    }

    ws = WSClient(session=pod.api.session, url=pod.api.url, token=pod.api.config.users["self"]["token"])
    execute_response = ws.get(trace=trace, **pod.api_kwargs(**kwargs))
    print("execute response: ", execute_response)
    for msg in execute_response:
        print(msg)
    return execute_response

