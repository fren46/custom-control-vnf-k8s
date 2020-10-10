FROM gcr.io/airspot/ruleset-image-base:0.4.4

ADD ./app /app
COPY ./app/app_functions app/app_functions

# nice to have an interactive shell
RUN pip install ipython websocket-client
ADD ipython_config.py /root/.ipython/profile_default/


# uncomment for subjects redis support
RUN pip install krules-subjects-storage-redis==0.4.4
RUN pip install krules-subjects-storage-k8s==0.4.43


# uncomment for subjects mongodb support
# RUN pip install krules-subjects-storage-mongodb==0.2.4
