# MyMolue

A modern Nigerian ride-hailing platform built around **fare negotiation** and **shared rides**.

## Current MVP

- Rider and driver accounts
- Secure password hashing with Bcrypt
- Rider ride requests with pickup, destination and proposed fare
- Optional shared-ride requests
- Drivers can view open requests and submit counter-offers
- Riders can accept driver offers
- Ride lifecycle statuses: requested, offer received, accepted, arriving, in progress, completed and cancelled
- SQLite database for local development
- Gunicorn production start command
- Responsive web interface

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

## Environment

Set `SECRET_KEY` in production. The development fallback is intentionally simple and should not be used for a deployed application.

## Roadmap

Maps and geolocation, real-time driver matching, payments, trip tracking, notifications, driver verification, ratings, admin operations and production-grade migrations are next steps.
