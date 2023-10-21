lint:
	@echo "Linting with isort + black + flakehell"
	@isort --check-only --diff .
	@black --check --diff .
lint-fix:
	@echo "Fix Linting with isort + black + flakehell"
	@isort .
	@black .