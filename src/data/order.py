"""
order.py
--------
Order Database for SnackStack Multi-Agent System.

This module exposes ORDER_DB, a dictionary keyed by order_id where each
value is a dictionary representing one order. The Order Agent (and the
Orchestrator) can import ORDER_DB and use the helper functions below to
look up, filter, and update orders.
"""

from typing import List, Dict, Optional, Any


ORDER_DB: Dict[str, Dict[str, Any]] = {
    "ORD1001": {
        "order_id": "ORD1001",
        "item_id": 1,
        "item_name": "Margherita Pizza",
        "customer_name": "Aditya Rao",
        "customer_email": "aditya.rao@example.com",
        "status": "Delivered",
        "price": 299,
        "order_date": "2025-01-10",
        "estimated_delivery": "2025-01-10",
        "tracking_id": "TRK-8841-AR",
    },
    "ORD1002": {
        "order_id": "ORD1002",
        "item_id": 3,
        "item_name": "Butter Chicken",
        "customer_name": "Priya Singh",
        "customer_email": "priya.singh@example.com",
        "status": "Out for Delivery",
        "price": 379,
        "order_date": "2025-01-12",
        "estimated_delivery": "2025-01-12",
        "tracking_id": "TRK-7723-PS",
    },
    "ORD1003": {
        "order_id": "ORD1003",
        "item_id": 4,
        "item_name": "Vegan Buddha Bowl",
        "customer_name": "Karan Mehta",
        "customer_email": "karan.mehta@example.com",
        "status": "Preparing",
        "price": 319,
        "order_date": "2025-01-13",
        "estimated_delivery": "2025-01-13",
        "tracking_id": "TRK-6612-KM",
    },
    "ORD1004": {
        "order_id": "ORD1004",
        "item_id": 6,
        "item_name": "Paneer Tikka",
        "customer_name": "Sneha Iyer",
        "customer_email": "sneha.iyer@example.com",
        "status": "Confirmed",
        "price": 199,
        "order_date": "2025-01-14",
        "estimated_delivery": "2025-01-14",
        "tracking_id": "TRK-5590-SI",
    },
    "ORD1005": {
        "order_id": "ORD1005",
        "item_id": 8,
        "item_name": "Mango Lassi",
        "customer_name": "Rohan Das",
        "customer_email": "rohan.das@example.com",
        "status": "Cancelled",
        "price": 99,
        "order_date": "2025-01-14",
        "estimated_delivery": "N/A",
        "tracking_id": "TRK-4487-RD",
    },
}


# def get_all_orders() -> List[Dict[str, Any]]:
#     """Return all orders as a list of dicts."""
#     return list(ORDER_DB.values())


# def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
#     """Return a single order dict matching the given order_id, or None."""
#     return ORDER_DB.get(order_id)


# def get_orders_by_customer(customer_name: str) -> List[Dict[str, Any]]:
#     """Case-insensitive search for all orders placed by a given customer."""
#     customer_name = customer_name.lower()
#     return [
#         o for o in ORDER_DB.values()
#         if o["customer_name"].lower() == customer_name
#     ]


# def get_orders_by_email(customer_email: str) -> List[Dict[str, Any]]:
#     """Case-insensitive search for all orders tied to a given email."""
#     customer_email = customer_email.lower()
#     return [
#         o for o in ORDER_DB.values()
#         if o["customer_email"].lower() == customer_email
#     ]


# def filter_by_status(status: str) -> List[Dict[str, Any]]:
#     """Return all orders matching a given status (case-insensitive)."""
#     status = status.lower()
#     return [o for o in ORDER_DB.values() if o["status"].lower() == status]


# def get_order_by_tracking_id(tracking_id: str) -> Optional[Dict[str, Any]]:
#     """Return the order matching a given tracking_id, or None."""
#     for order in ORDER_DB.values():
#         if order["tracking_id"] == tracking_id:
#             return order
#     return None


# def update_order_status(order_id: str, new_status: str) -> bool:
#     """Update the status of an existing order. Returns True on success."""
#     if order_id in ORDER_DB:
#         ORDER_DB[order_id]["status"] = new_status
#         return True
#     return False


# def add_order(order: Dict[str, Any]) -> bool:
#     """Add a new order to the database, keyed by its order_id."""
#     order_id = order.get("order_id")
#     if not order_id or order_id in ORDER_DB:
#         return False
#     ORDER_DB[order_id] = order
#     return True


# if __name__ == "__main__":
#     # Quick manual smoke test
#     for order in get_all_orders():
#         print(f"{order['order_id']} | {order['item_name']:<20} | {order['customer_name']:<15} "
#               f"| {order['status']:<16} | ₹{order['price']:<4} | {order['tracking_id']}")