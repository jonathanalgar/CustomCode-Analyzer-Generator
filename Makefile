.PHONY: install check-python-format check-python-lint check-csharp test-python test-dotnet build-dotnet

install:
	poetry install --no-interaction --no-ansi

check-python-format:
	poetry run black --check agents/
	poetry run isort --check-only agents/

check-python-lint:
	poetry run mypy --explicit-package-bases --namespace-packages agents/
	poetry run flake8 agents/

check-csharp:
	cd agents/evaluation/CCAGTestGenerator && dotnet tool restore && dotnet csharpier --check .

test-python:
	poetry run pytest

test-dotnet:
	dotnet test --nologo --configuration Release agents/evaluation/CCAGTestGenerator/CCAGTestGenerator.sln

build-dotnet:
	dotnet restore agents/evaluation/CCAGTestGenerator/CCAGTestGenerator.sln
	dotnet build --nologo --configuration Release agents/evaluation/CCAGTestGenerator/CCAGTestGenerator.sln
	dotnet publish --nologo --configuration Release agents/evaluation/CCAGTestGenerator/CCAGTestGenerator.sln
