lint:
	@echo "Linting with isort + black + flakehell"
	@isort --check-only --diff .
	@black --check --diff .
lint-fix:
	@echo "Fix Linting with isort + black + flakehell"
	@isort .
	@black .

bump-patch:
	@echo "Bumping version patch"
	@poetry version patch
	@git add pyproject.toml
	@git commit -m "Bump patch version"

tag:
	@echo "Tagging version"
	@git tag v`poetry version -s`