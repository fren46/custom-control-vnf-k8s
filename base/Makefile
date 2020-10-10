SHELL=/bin/bash

BASE_VERSION = `cat VERSION`
BASE_TMP_VERSION = `cat VERSION.tmp`
DOCKER_REGISTRY=`krules-py profile get-value docker_registry`
NAMESPACE=`krules-py profile get-value namespace`

.PHONY: clean

all: push .lastResources

checkLocalBuild:
	docker images |grep use-case-tim-base|grep  ${BASE_VERSION}|wc -l| grep -o "[0-9]\+" > .BUILD_NEEDED
	if [[`cat .BUILD_NEEDED` = 0]]; then \
  	touch Dockerfile; \
  	fi; \
  	rm .BUILD_NEEDED;

VERSION: checkLocalBuild Dockerfile app/*.py
	cp VERSION VERSION.tmp && \
	bumpversion --current-version ${BASE_VERSION}  patch VERSION.tmp --allow-dirty && \
	docker build -t  ${DOCKER_REGISTRY}/use-case-tim-base:${BASE_TMP_VERSION}  -t ${DOCKER_REGISTRY}/use-case-tim-base:latest . && \
	cp VERSION.tmp VERSION && rm VERSION.tmp

push: VERSION
	docker push ${DOCKER_REGISTRY}/use-case-tim-base:${BASE_VERSION}

.lastResources: VERSION k8s/*
	kubectl kustomize k8s  | kubectl apply -n ${NAMESPACE}  -f - \
	&& echo `date` > ".lastResources"

clean:
	rm -f VERSION.tmp .lastResources .BUILD_NEEDED