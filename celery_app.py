from celery import Celery
from mongoengine import connect
import os
import logging
from dotenv import load_dotenv
load_dotenv()

# Set up logging for Celery worker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | transaction_worker | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('transaction_worker')

celery = Celery(
    'transaction',
    broker=f"redis://{os.getenv('CELERY_BROKER_HOST', 'localhost')}:{os.getenv('CELERY_BROKER_PORT', 6379)}/0",
    backend=f"redis://{os.getenv('CELERY_BROKER_HOST', 'localhost')}:{os.getenv('CELERY_BROKER_PORT', 6379)}/0",
    # tasks=['stock.unreserve_stock','stock.reserve_stock', 'stock.finalise_stock_purchase','transaction.create','cart.completeCheckout','cart.unfreeze'],
)
celery.conf.task_routes = {
    'transaction.*': {'queue': 'transaction_queue'},
    'cart.*': {'queue': 'cart_queue'},
    'stock.*': {'queue': 'stock_queue'},
}
celery.autodiscover_tasks()


# Initialize MongoDB connection
connect(
    db=os.getenv('MONGODB_DB', 'devopsshowcase'),
    username=os.getenv('MONGODB_USERNAME'),
    password=os.getenv('MONGODB_PASSWORD'),
    host=os.getenv('MONGODB_HOST', 'localhost'),
    port=int(os.getenv('MONGODB_PORT', 27017)),
    authentication_source=os.getenv('MONGODB_AUTH_SOURCE', 'devopsshowcase')
)
logger.info(f"Transaction Celery worker connected to MongoDB")


from app.services.transaction_service import create_transaction
@celery.task(name="transaction.create")
def create_transaction_task(cart_id, transaction_value):
    """
    Create a new transaction.

    Called by cart service when checkout is initiated.
    """
    logger.info(f"TASK RECEIVED | transaction.create | cart_id={cart_id} | value={transaction_value}")
    result = create_transaction(cart_id, transaction_value)
    if result.get("ok"):
        logger.info(f"TASK SUCCESS | transaction.create | cart_id={cart_id} | transaction_id={result.get('transaction', {}).get('id')}")
    else:
        logger.error(f"TASK FAILED | transaction.create | cart_id={cart_id} | error={result.get('message')}")
    return result



