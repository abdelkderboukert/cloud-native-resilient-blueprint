.PHONY: help validate validate-helm security-scan test up down deploy argocd-apply clean

help:
	@echo "Enterprise Event-Driven Micro-Platform (EEMP) Makefile"
	@echo "Available targets:"
	@echo "  validate       - Validate all Kubernetes manifests and kustomize assembly"
	@echo "  validate-helm  - Validate Helm chart templates, syntax, and values structure"
	@echo "  security-scan  - Audit repository for hardcoded secrets, antipatterns, and dependencies"
	@echo "  test           - Run Django application unit and integration tests"
	@echo "  up             - Start the local multi-tier Docker Compose environment"
	@echo "  down           - Stop and tear down the local Docker Compose environment"
	@echo "  deploy         - Deploy via kubectl scripts"
	@echo "  argocd-apply   - Apply declarative ArgoCD AppProject and Application manifests"
	@echo "  clean          - Remove build, coverage, and cache artifacts"

validate:
	python scripts/validate-manifests.py
	kubectl kustomize deploy/kubernetes/ > /dev/null
	@echo "All manifest validations passed."

validate-helm:
	python scripts/validate-helm.py

security-scan:
	python scripts/security-scan.py

test:
	@set USE_SQLITE=True
	@set KAFKA_TEST_MODE=True
	cd src/django-enterprise-api && python manage.py test

argocd-apply:
	kubectl apply -f deploy/argocd/appproject.yaml
	kubectl apply -f deploy/argocd/application.yaml

up:
	docker compose up -d --build

down:
	docker compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f src/django-enterprise-api/db.sqlite3
