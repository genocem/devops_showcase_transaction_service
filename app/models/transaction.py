"""
Transaction model for managing transactions
"""
from typing import Any
from mongoengine import Document, StringField, DateTimeField, LazyReferenceField, FloatField
from datetime import datetime,timezone


class Transaction(Document):
    id: Any

    # lazy reference field sounded cooler than referencefield so imma use it
    # just don't forget to use .fetch() to get the whole project in the future
    # Storing cart_id as string since Cart is in a different service
    # The event processor will pass the cart_id when creating a transaction
    # nah just keeping normal id and i'll add it
    cart_id = StringField(required=True)
    transaction_value = FloatField(required=True, min_value=0)
    currency = StringField(default="dollar")
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    updated_at = DateTimeField(default=datetime.now(timezone.utc))
    status = StringField(default="pending", choices=["pending", "completed", "failed", "refunded"])


    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'cart_id': self.cart_id,
            'transaction_value': self.transaction_value,
            'currency': self.currency,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else None,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else None,
            'status': self.status
        }
