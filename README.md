# Transaction Service

Flask microservice for managing transactions. Handles transaction creation from cart checkouts, status tracking, and payment confirmations. Uses Celery for async event processing.

## Structure

```
transaction_service/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Configuration
│   ├── models/transaction.py    # MongoDB model
│   ├── routes/transaction_routes.py # API endpoints
│   ├── services/transaction_service.py # Business logic
│   └── utils/                   # Decorators, error handlers, logging
├── celery_app.py                # Celery worker
├── run.py                       # Entry point
├── Dockerfile
├── Jenkinsfile
└── requirements.txt
```

## Requirements

- Python 3.9+
- MongoDB
- Redis

## Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run --host=0.0.0.0 --port=5000

# Celery worker (separate terminal)
celery -A celery_app worker -n transaction_worker --loglevel=info -Q transaction_queue
```

## Environment Variables

```env
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB=devopsshowcase
MONGODB_USER=appuser
MONGODB_PASSWORD=apppassword
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Celery Tasks

### Worker Setup

The Transaction Service worker listens on `transaction_queue` and registers tasks from `celery_app.py`.

```bash
celery -A celery_app worker -n transaction_worker --loglevel=info -Q transaction_queue
```

### Tasks Exposed by Transaction Service

| Task Name | Purpose | Triggered By |
|-----------|---------|--------------|
| `transaction.create` | Creates a pending transaction for a cart checkout | Cart Service |

### External Tasks Sent by Transaction Service

During transaction status changes, this service sends callback tasks to the cart queue:

| Task Name | Purpose |
|-----------|---------|
| `cart.completeCheckout` | Finalize the cart after a successful transaction |
| `cart.unfreeze` | Restore the cart when the transaction fails |
| `cart.processRefund` | Apply refund-related cart state changes |

## API Endpoints

Base URL: `/api/transactions`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get all transactions |
| GET | `/<transaction_id>` | Get specific transaction |
| GET | `/cart/<cart_id>` | Get transactions for cart |
| POST | `/` | Create transaction |
| PUT | `/<transaction_id>` | Update status |
| DELETE | `/<transaction_id>` | Delete transaction |

## Transaction Statuses

| Status | Description |
|--------|-------------|
| `pending` | Awaiting payment |
| `completed` | Payment successful |
| `failed` | Payment failed |
| `refunded` | Transaction refunded |

## Transaction Flow

1. Cart Checkout - Transaction created with `pending` status
2. Payment Processing - External gateway (simulated)
3. Status Update:
   - `completed` - Cart checked out, stock finalized
   - `failed` - Cart unfrozen, stock released
   - `refunded` - Reverse transaction, restore stock

## Docker

```bash
docker build -t transaction_service .
docker run -p 5000:5000 --env-file .env transaction_service
```

## License

MIT License
