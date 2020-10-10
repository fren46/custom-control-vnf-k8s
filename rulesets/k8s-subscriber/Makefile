SHELL=/bin/bash

RULESET_VERSION = `cat VERSION`
RULESET_TMP_VERSION = `cat VERSION.tmp`
DOCKER_REGISTRY=`krules-py profile get-value docker_registry`
NAMESPACE=`krules-py profile get-value namespace`

.PHONY: clean

all: .lastResources

Dockerfile: Dockerfile.origin
	krules-py ruleset build-dockerfile;


VERSION: Dockerfile app/*.py
	cp VERSION VERSION.tmp && \
	bumpversion --current-version ${RULESET_VERSION} patch VERSION.tmp --allow-dirty && \
	docker build -t ${DOCKER_REGISTRY}/use-case-tim-k8s-subscriber:${RULESET_TMP_VERSION} -t ${DOCKER_REGISTRY}/use-case-tim-k8s-subscriber:latest . &&\
	cp VERSION.tmp VERSION && rm VERSION.tmp

push: VERSION
	docker push ${DOCKER_REGISTRY}/use-case-tim-k8s-subscriber:${RULESET_VERSION}

.lastResources: VERSION k8s/*
	docker images |grep ${DOCKER_REGISTRY}/use-case-tim-k8s-subscriber|grep  ${RULESET_VERSION}|wc -l| grep -o "[0-9]\+" > .UPDATE_NEEDED
	if [[ `cat .UPDATE_NEEDED` = 1 ]]; then \
		make push; \
	fi && \
	krules-py ruleset patch --set-image ruleset=${DOCKER_REGISTRY}/use-case-tim-k8s-subscriber:${RULESET_VERSION} | kubectl apply -n ${NAMESPACE}  -f - && \
	echo `date` > ".lastResources" && rm .UPDATE_NEEDED

clean:
	rm -f Dockerfile VERSION.tmp .lastResources .UPDATE_NEEDED
