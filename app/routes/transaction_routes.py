"""
Transaction routes for managing transactions
"""
from flask import Blueprint, jsonify, request
from app.services.transaction_service import (
    create_transaction,
    get_all_transactions,
    get_transaction_by_id,
    get_transactions_by_cart,
    delete_transaction
)

transaction_bp = Blueprint('transaction', __name__)

error_map = {
    "VALIDATION_ERROR": 400,
    "NOT_FOUND": 404,
    "INVALID_CART": 400
}


@transaction_bp.route('/', methods=['GET'])
def get_transactions():
    """Get all transactions"""
    result = get_all_transactions()

    if result["ok"]:
        return jsonify({
            'success': True,
            'transactions': result['transactions']
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), 500


@transaction_bp.route('/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get a specific transaction by ID"""
    result = get_transaction_by_id(transaction_id)

    if result["ok"]:
        return jsonify({
            'success': True,
            'transaction': result['transaction']
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), error_map.get(result.get("error", ""), 500)


@transaction_bp.route('/cart/<cart_id>', methods=['GET'])
def get_cart_transactions(cart_id):
    """Get all transactions for a specific cart"""
    result = get_transactions_by_cart(cart_id)

    if result["ok"]:
        return jsonify({
            'success': True,
            'transactions': result['transactions']
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), error_map.get(result.get("error", ""), 500)


# This endpoint will mainly be called by the event processor
# when a cart checkout event is received
#useless remove in future
@transaction_bp.route('/', methods=['POST'])
def add_transaction():
    """Create a new transaction (typically called via event processor)"""
    data = request.get_json() or {}

    cart_id = data.get("cart_id")
    transaction_value = data.get("transaction_value")
    currency = data.get("currency", "dollar")

    if not cart_id or transaction_value is None:
        return jsonify({
            'success': False,
            'message': 'cart_id and transaction_value are required'
        }), 400

    result = create_transaction(cart_id, transaction_value, currency)

    if result["ok"]:
        return jsonify({
            'success': True,
            'message': result['message'],
            'transaction': result['transaction']
        }), 201
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), error_map.get(result.get("error", ""), 500)


@transaction_bp.route('/<transaction_id>', methods=['DELETE'])
def remove_transaction(transaction_id):
    """Delete a transaction"""
    result = delete_transaction(transaction_id)

    if result["ok"]:
        return jsonify({
            'success': True,
            'message': result['message']
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), error_map.get(result.get("error", ""), 500)


@transaction_bp.route('/<transaction_id>', methods=['PUT'])
def update_transaction_status(transaction_id):
    """
    Update status of a transaction.

    Valid statuses: pending, completed, failed, refunded
    Triggers events based on status change (e.g., cart.completeCheckout on completed)
    """
    from app.services.transaction_service import updateStatus

    data = request.get_json() or {}
    status = data.get("status")
    cart_id = data.get("cart_id")

    if not status:
        return jsonify({
            'success': False,
            'message': 'status is required'
        }), 400

    result = updateStatus(transaction_id, status, cart_id)

    if result["ok"]:
        return jsonify({
            'success': True,
            'message': result['message'],
            'transaction': result['transaction']
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), error_map.get(result.get("error", ""), 500)
