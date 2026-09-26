from src.logger import setup_logger
from langchain_core.tools import tool
from src.data.order import ORDER_DB
from typing import Any, Dict, Optional

logger = setup_logger("order_tools")

"""----helper functions for order tools----"""

def normalize_order_id(id: str) -> str:
    """Normalize the order ID by converting it to lowercase and stripping whitespace.
    Accept 'ORD101', 'ord102','ORD-101','ord-101' or just '101'-> 'ORD101' etc."""
    
    id = id.upper().strip()
    if id.startswith("ORD-"):
        id = id.replace("ORD-", "ORD")
    elif id.isdigit():
        id = f"ORD{id}"
    return id

def normalize_order_by_tracking_number(tracking_number: str) -> str:
    """Normalize the order tracking number by converting it to lowercase and stripping whitespace.
    Accept 'TRK-7723-PS', 'TRK123ps', 'trk1234ps', 'TRK-1234-PS',  or just '1234-az'-> 'TRK-1234-AZ' etc.""" 
    tracking_number = tracking_number.upper().strip()
    if tracking_number.startswith("TRK"):
        if tracking_number[3].isdigit():
            tracking_number = tracking_number.replace("TRK", "TRK-")
        if tracking_number[8].isalpha():
            tracking_number = tracking_number.replace(tracking_number[8], "-"+tracking_number[8])
    elif tracking_number.isdigit():
        tracking_number = f"TRK-{tracking_number}"
    return tracking_number

def get_order_by_tracking_id(tracking_id: str) -> Optional[Dict[str, Any]]:
    """Return the order matching a given tracking_id (case-insensitive), or None."""
    tracking_id = tracking_id.lower()
    for order in ORDER_DB.values():
        if order["tracking_id"].lower() == tracking_id:
            return order
    return None
def lookup_by_email(email: str) -> list:
    logger.info("Looking up orders by email: %s", email)
    email = email.lower().strip()
    for oid,order in ORDER_DB.items():
        if order["customer_email"].lower().strip() == email:
            return {"order_id": oid, "order": order}
    return None

# @tool
# def search_order_DB(query: str) -> list:
#     logger.info("Searching order DB for query: %s", query)
#     result = [order for order in ORDER_DB if query.lower() in order["name"].lower()]
#     if not result:
#         return "No orders found matching your query."
#     return result

@tool
def get_order_status(identifier: str) -> dict:
    """Look up the current status of a customer order.

    Args:
        identifier: an order ID (e.g. "ORD101") OR a trackinng number (e.g. "TRK-1234-PS") OR a customer email address
    """
    logger.info("Getting order status for identifier: %s", identifier)
    identifier = identifier.strip()
    if "@" in identifier:
        match=lookup_by_email(identifier)
        if match:
            oid = match["order_id"]
            order = match["order"]
        else:
            return f"No orders found for email: {identifier}"
    elif identifier.upper().startswith("ORD"):
        identifier = normalize_order_id(identifier)
        if identifier in ORDER_DB:
            oid = identifier
            order = ORDER_DB[identifier]
        else:
            return f"No orders found for order ID: {identifier}"
    elif identifier.upper().startswith("TRK"):
        tracking_id = normalize_order_by_tracking_number(identifier)
        order_found = False
        for oid, order in ORDER_DB.items():
            if order.get("tracking_id", "").upper().strip() == tracking_id:
                oid = oid
                order = order
                order_found = True
                logger.info("Order found for tracking number: %s", tracking_id)
                break
        if not order_found:
            return f"No orders found for tracking number: {tracking_id}"
    else:
        return f"Unrecognized identifier format: {identifier}, order not found"

    info = (
        f"Order {oid}:\n"
        f"  Customer : {order['customer_name']} ({order['customer_email']})\n"
        f"  Item  : {order['item_name']}\n"
        f"  Price    : ${order['price']:,}\n"
        f"  Status   : {order['status']}\n"
        f"  Ordered  : {order['order_date']}\n"
        f"  ETA      : {order['estimated_delivery']}"
    )
    if order.get("delay_reason"):
        info += f"\n  Delay    : {order['delay_reason']}"
    return info


if __name__ == "__main__":
    # Quick manual smoke tests
    print(get_order_status.invoke({"identifier": "ORD1002"}))
    print("\n---\n")
    print(get_order_status.invoke({"identifier": "TRK-6612-KM"}))
    print("\n---\n")
    print(get_order_status.invoke({"identifier": "rohan.das@example.com"}))
    print("\n---\n")
    print(get_order_status.invoke({"identifier": "UNKNOWN123"}))