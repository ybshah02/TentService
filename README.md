# TentService

TentService is the backend API for Tent, a platform designed to connect local artisans and vendors with customers through a marketplace and discovery application. It manages market event scheduling, vendor profiles, and social discovery features.

## Purpose
The service exists to centralize data for local markets, providing a structured way for vendors to showcase their work and for customers to discover events happening in their community.

## Core Features
- Market Management: Create and list market events with location-based discovery.
- Vendor Profiles: Manage business identities, categories, and social links.
- Social Feed: Support for vendor posts, likes, and comments.
- Discovery API: Geographic and category-based filtering for events and vendors.

## Tech Stack
- FastAPI (Python)
- Supabase (Database & Authentication)
- SQLAlchemy (Asynchronous database operations)
- Docker & Fly.io (Deployment ready)

## Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   - Copy `.env.example` to `.env`.
   - Provide `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and `DATABASE_URL`.
4. Seed the database:
   ```bash
   python -m db.seed
   ```
5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

## API Documentation
Once the server is running, documentation is available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`
