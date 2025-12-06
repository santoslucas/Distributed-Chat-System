# Distributed-Chat-System

## To execute the tests:
docker-compose up -d
docker-compose exec tester pip install -r requirements-dev.txt
docker-compose exec tester pytest

## To run the local server:
docker-compose up --build 