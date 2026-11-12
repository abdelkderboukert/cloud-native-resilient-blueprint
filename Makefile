.PHONY: help validate validate-helm security-scan test up down deploy teardown argocd-apply clean

HELM_CHART := deploy/helm/enterprise-platform

help:
	@echo "Enterprise Event-Driven Micro-Platform (EEMP) Makefile"
	@echo "Available targets:"
	@echo "  validate       - Validate and render the Helm chart"
	@echo "  validate-helm  - Validate Helm chart templates, syntax, and values structure"
	@echo "  security-scan  - Audit repository for hardcoded secrets, antipatterns, and dependencies"
	@echo "  test           - Run Django application unit and integration tests"
	@echo "  up             - Start the local multi-tier Docker Compose environment"
	@echo "  down           - Stop and tear down the local Docker Compose environment"
	@echo "  deploy         - Deploy the Helm chart to the current Kubernetes context"
	@echo "  teardown       - Uninstall the Helm release"
	@echo "  argocd-apply   - Apply declarative ArgoCD AppProject and Application manifests"
	@echo "  clean          - Remove build, coverage, and cache artifacts"

validate: validate-helm

validate-helm:
	python scripts/validate-helm.py
	helm lint $(HELM_CHART)
	helm lint $(HELM_CHART) --values $(HELM_CHART)/values-dev.yaml
	helm lint $(HELM_CHART) --values $(HELM_CHART)/values-prod.yaml
	helm template enterprise-platform $(HELM_CHART) --values $(HELM_CHART)/values.yaml > /dev/null
	helm template enterprise-platform $(HELM_CHART) --values $(HELM_CHART)/values-dev.yaml > /dev/null
	helm template enterprise-platform $(HELM_CHART) --values $(HELM_CHART)/values-prod.yaml > /dev/null

security-scan:
	python scripts/security-scan.py

test:
	@set USE_SQLITE=True
	@set KAFKA_TEST_MODE=True
	cd src/django-enterprise-api && python manage.py test

argocd-apply:
	kubectl apply -f $(HELM_CHART)/gitops/appproject.yaml
	kubectl apply -f $(HELM_CHART)/gitops/application.yaml

deploy:
	bash scripts/deploy.sh

teardown:
	bash scripts/teardown.sh

up:
	docker compose up -d --build

down:
	docker compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f src/django-enterprise-api/db.sqlite3
