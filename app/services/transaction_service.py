"""
Transaction service
"""
from datetime import datetime
from app.models.transaction import Transaction
from mongoengine.errors import ValidationError
from bson import ObjectId
from app.utils.logging_config import logger, log_error, log_transaction_event, log_celery_task, log_db_operation

from celery import Celery
import os
celery = Celery(
    'transaction_service',
    broker=f"redis://{os.getenv('CELERY_BROKER_HOST', 'localhost')}:{os.getenv('CELERY_BROKER_PORT', 6379)}/0"
)
celery.conf.task_routes = {
    'transaction.*': {'queue': 'transaction_queue'},
    'cart.*': {'queue': 'cart_queue'},
    'stock.*': {'queue': 'stock_queue'},
}


def create_transaction(cart_id, transaction_value, currency="dollar"):
    """Create a new transaction"""
    try:
        logger.info(f"Creating transaction | cart_id={cart_id} | value={transaction_value} | currency={currency}")

        transaction = Transaction(
            cart_id=cart_id,
            transaction_value=transaction_value,
            currency=currency,
            status="pending"
        ).save()

        log_db_operation("CREATE", "transactions", str(transaction.id))
        log_transaction_event(str(transaction.id), cart_id, "CREATED", "pending", transaction_value)
        logger.info(f"Transaction created | id={transaction.id} | cart_id={cart_id} | value={transaction_value}")

        return {
            "ok": True,
            "message": f"Transaction created successfully for cart: {cart_id}",
            "transaction": transaction.to_dict()
        }
    except ValidationError as err:
        log_error("create_transaction", err, {"cart_id": cart_id})
        return {
            "ok": False,
            "error": "VALIDATION_ERROR",
            "message": str(err)
        }
    except Exception as err:
        log_error("create_transaction", err, {"cart_id": cart_id})
        return {
            "ok": False,
            "message": str(err)
        }


def get_all_transactions():
    """Get all transactions"""
    try:
        transactions = Transaction.objects()
        logger.debug(f"Retrieved all transactions | count={len(transactions)}")
        return {
            "ok": True,
            "transactions": [t.to_dict() for t in transactions]
        }
    except Exception as err:
        log_error("get_all_transactions", err)
        return {
            "ok": False,
            "message": str(err)
        }


def get_transaction_by_id(transaction_id):
    """Get a specific transaction by ID"""
    try:
        if not ObjectId.is_valid(transaction_id):
            logger.warning(f"Invalid transaction ID format | transaction_id={transaction_id}")
            return {
                "ok": False,
                "error": "VALIDATION_ERROR",
                "message": "Invalid transaction ID format"
            }

        transaction = Transaction.objects(id=transaction_id).first()

        if not transaction:
            logger.warning(f"Transaction not found | transaction_id={transaction_id}")
            return {
                "ok": False,
                "error": "NOT_FOUND",
                "message": "Transaction not found"
            }

        logger.debug(f"Transaction retrieved | transaction_id={transaction_id}")
        return {
            "ok": True,
            "transaction": transaction.to_dict()
        }
    except Exception as err:
        log_error("get_transaction_by_id", err, {"transaction_id": transaction_id})
        return {
            "ok": False,
            "message": str(err)
        }


def get_transactions_by_cart(cart_id):
    """Get all transactions for a specific cart"""
    try:
        transactions = Transaction.objects(cart_id=cart_id)
        logger.debug(f"Retrieved transactions for cart | cart_id={cart_id} | count={len(transactions)}")
        return {
            "ok": True,
            "transactions": [t.to_dict() for t in transactions]
        }
    except Exception as err:
        log_error("get_transactions_by_cart", err, {"cart_id": cart_id})
        return {
            "ok": False,
            "message": str(err)
        }


def delete_transaction(transaction_id):
    """Delete a transaction"""
    try:
        if not ObjectId.is_valid(transaction_id):
            logger.warning(f"Invalid transaction ID format | transaction_id={transaction_id}")
            return {
                "ok": False,
                "error": "VALIDATION_ERROR",
                "message": "Invalid transaction ID format"
            }

        transaction = Transaction.objects(id=transaction_id).first()

        if not transaction:
            logger.warning(f"Transaction not found for deletion | transaction_id={transaction_id}")
            return {
                "ok": False,
                "error": "NOT_FOUND",
                "message": "Transaction not found"
            }

        cart_id = transaction.cart_id
        transaction.delete()
        logger.info(f"Transaction deleted | transaction_id={transaction_id} | cart_id={cart_id}")
        log_db_operation("DELETE", "transactions", transaction_id)

        return {
            "ok": True,
            "message": "Transaction deleted successfully"
        }
    except Exception as err:
        log_error("delete_transaction", err, {"transaction_id": transaction_id})
        return {
            "ok": False,
            "message": str(err)
        }



def updateStatus(transaction_id, status, cart_id=None):
    """
    Update the status of a transaction and trigger related events.

    Handles status transitions and emits appropriate Celery tasks:
    - completed: Sends cart.completeCheckout
    - failed: Sends cart.unfreeze to restore cart

    Args:
        transaction_id: ID of the transaction to update
        status: New status (pending, completed, failed, refunded)
        cart_id: Associated cart ID for event routing
    """
    try:
        logger.info(f"Updating transaction status | transaction_id={transaction_id} | new_status={status} | cart_id={cart_id}")

        if not ObjectId.is_valid(transaction_id):
            logger.warning(f"Invalid transaction ID format | transaction_id={transaction_id}")
            return {
                "ok": False,
                "error": "VALIDATION_ERROR",
                "message": "Invalid transaction ID format"
            }
        valid_statuses = ["pending", "completed", "failed", "refunded"]
        if status not in valid_statuses:
            logger.warning(f"Invalid status provided | transaction_id={transaction_id} | status={status}")
            return {
                "ok": False,
                "error": "VALIDATION_ERROR",
                "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }
        if not cart_id:
            logger.warning(f"Missing cart_id for status update | transaction_id={transaction_id} | status={status}")
            return {
                "ok": False,
                "error": "VALIDATION_ERROR",
                "message": "cart_id is required for status updates"
            }

        if status =="refunded":
            transaction = Transaction.objects(id=transaction_id,cart_id=cart_id,status='completed').first()
            if not transaction:
                logger.warning(f"Transaction not found or not completed to refund | transaction_id={transaction_id} | cart_id={cart_id}")
                return {
                    "ok": False,
                    "error": "NOT_FOUND",
                    "message": "Transaction not found"
                }
        else:
            transaction = Transaction.objects(id=transaction_id,cart_id=cart_id,status='pending').first()
            if not transaction:
                logger.warning(f"Transaction not found or not pending | transaction_id={transaction_id} | cart_id={cart_id}")
                return {
                    "ok": False,
                    "error": "NOT_FOUND",
                    "message": "Transaction not found"
                }

        old_status = transaction.status
        transaction.status = status
        transaction.updated_at = datetime.now()
        transaction.save()
        log_transaction_event(transaction_id, cart_id, "STATUS_CHANGE", status, transaction.transaction_value)
        logger.info(f"Transaction status updated | transaction_id={transaction_id} | old_status={old_status} | new_status={status}")

        # Handle status-specific actions
        if status == "completed":
            log_celery_task("cart.completeCheckout", [cart_id], "SENT")
            celery.send_task('cart.completeCheckout', args=[cart_id])
            logger.info(f"Sent cart.completeCheckout task | cart_id={cart_id}")
        elif status == "failed":
            log_celery_task("cart.unfreeze", [cart_id], "SENT")
            celery.send_task('cart.unfreeze', args=[cart_id])
            logger.info(f"Sent cart.unfreeze task | cart_id={cart_id}")
        elif status == "refunded":
            # Future implementation for refunds can be added here
            logger.info(f"Refund process to be implemented | transaction_id={transaction_id}")
            celery.send_task('cart.processRefund', args=[cart_id])
            log_celery_task("cart.processRefund", [cart_id], "SENT")

        return {
            "ok": True,
            "message": f"Transaction status updated from '{old_status}' to '{status}'",
            "transaction": transaction.to_dict()
        }
    except ValidationError as err:
        log_error("updateStatus", err, {"transaction_id": transaction_id, "status": status})
        return {
            "ok": False,
            "error": "VALIDATION_ERROR",
            "message": str(err)
        }
    except Exception as err:
        log_error("updateStatus", err, {"transaction_id": transaction_id, "status": status})
        return {
            "ok": False,
            "message": str(err)
        }





