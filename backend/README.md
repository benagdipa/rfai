# Network Performance Monitoring App

## Setup

### Backend
1. Install Python 3.9+ and dependencies: `pip install -r requirements.txt`
2. Configure `.env` with your credentials
3. Run Redis: `redis-server`
4. Start Celery: `celery -A tasks.celery_config worker -l info`
5. Run the server: `uvicorn main:app --host 0.0.0.0 --port 8000`
