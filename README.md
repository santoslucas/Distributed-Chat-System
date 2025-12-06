# Distributed-Chat-System

## To run the tests:
- docker-compose up -d
- docker-compose exec tester pip install -r requirements-dev.txt
- docker-compose exec tester pytest auth/tests chat/tests tests/integration/test_backend.py tests/concurrency

## To run the frontend tests:
These tests should be run locally. 

Playwright should be installed. To install playwright:
- pip install pytest-playwright
- playwright install

To run the test:
- pytest tests/integration/test_frontend.py

## To run the local server:
- docker-compose up --build 