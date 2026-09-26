"""
menu.py
--------
Menu Catalog for SnackStack Multi-Agent System.

This module exposes MENU_CATALOG, a list of dictionaries where each
dictionary represents one dish available in the system. The Menu Agent
(and the Orchestrator) can import MENU_CATALOG and use the helper
functions below to filter/search dishes.
"""

from typing import List, Dict, Optional, Any

#---Menu Catalog Vector Store---#
MENU_CATALOG: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Margherita Pizza",
        "category": "Main Course",
        "cuisine": "Italian",
        "price": 299,
        "rating": 4.7,
        "dietary_tags": ["Veg"],
        "description": "Classic thin crust with tomato, mozzarella, basil",
        "availability": True,
    },
    {
        "id": 2,
        "name": "Vegan Pasta Primavera",
        "category": "Main Course",
        "cuisine": "Italian",
        "price": 349,
        "rating": 4.5,
        "dietary_tags": ["Vegan"],
        "description": "Penne with seasonal vegetables, olive oil, garlic",
        "availability": True,
    },
    {
        "id": 3,
        "name": "Butter Chicken",
        "category": "Main Course",
        "cuisine": "Indian",
        "price": 379,
        "rating": 4.9,
        "dietary_tags": ["GF"],
        "description": "Creamy tomato curry with tender chicken and naan",
        "availability": True,
    },
    {
        "id": 4,
        "name": "Vegan Buddha Bowl",
        "category": "Main Course",
        "cuisine": "Fusion",
        "price": 319,
        "rating": 4.6,
        "dietary_tags": ["Vegan", "GF"],
        "description": "Quinoa, chickpeas, avocado, greens, tahini",
        "availability": True,
    },
    {
        "id": 5,
        "name": "Classic Cheeseburger",
        "category": "Main Course",
        "cuisine": "American",
        "price": 259,
        "rating": 4.4,
        "dietary_tags": ["None"],
        "description": "Beef patty, cheddar, lettuce, tomato, brioche bun",
        "availability": True,
    },
    {
        "id": 6,
        "name": "Paneer Tikka",
        "category": "Starter",
        "cuisine": "Indian",
        "price": 199,
        "rating": 4.8,
        "dietary_tags": ["Veg", "GF"],
        "description": "Tandoor-grilled cottage cheese with peppers",
        "availability": True,
    },
    {
        "id": 7,
        "name": "Aglio e Olio",
        "category": "Main Course",
        "cuisine": "Italian",
        "price": 279,
        "rating": 4.5,
        "dietary_tags": ["Vegan"],
        "description": "Spaghetti with garlic, chilli, olive oil, parsley",
        "availability": True,
    },
    {
        "id": 8,
        "name": "Mango Lassi",
        "category": "Beverage",
        "cuisine": "Indian",
        "price": 99,
        "rating": 4.7,
        "dietary_tags": ["Veg", "GF"],
        "description": "Blended yogurt with Alphonso mango, cardamom",
        "availability": True,
    },
]


# def get_all_dishes() -> List[Dict[str, Any]]:
#     """Return the full menu catalog."""
#     return MENU_CATALOG


# def get_dish_by_id(dish_id: int) -> Optional[Dict[str, Any]]:
#     """Return a single dish dict matching the given id, or None."""
#     for dish in MENU_CATALOG:
#         if dish["id"] == dish_id:
#             return dish
#     return None


# def search_by_name(keyword: str) -> List[Dict[str, Any]]:
#     """Case-insensitive substring search on dish name."""
#     keyword = keyword.lower()
#     return [d for d in MENU_CATALOG if keyword in d["name"].lower()]


# def filter_by_cuisine(cuisine: str) -> List[Dict[str, Any]]:
#     """Return all dishes matching a given cuisine (case-insensitive)."""
#     cuisine = cuisine.lower()
#     return [d for d in MENU_CATALOG if d["cuisine"].lower() == cuisine]


# def filter_by_category(category: str) -> List[Dict[str, Any]]:
#     """Return all dishes matching a given category (case-insensitive)."""
#     category = category.lower()
#     return [d for d in MENU_CATALOG if d["category"].lower() == category]


# def filter_by_dietary_tag(tag: str) -> List[Dict[str, Any]]:
#     """Return dishes that include the given dietary tag (e.g. 'Vegan', 'GF')."""
#     tag = tag.lower()
#     return [
#         d for d in MENU_CATALOG
#         if any(tag == t.lower() for t in d["dietary_tags"])
#     ]


# def filter_by_price_range(min_price: float = 0, max_price: float = float("inf")) -> List[Dict[str, Any]]:
#     """Return dishes within an inclusive price range (INR)."""
#     return [d for d in MENU_CATALOG if min_price <= d["price"] <= max_price]


# def get_available_dishes() -> List[Dict[str, Any]]:
#     """Return only dishes currently marked as available."""
#     return [d for d in MENU_CATALOG if d["availability"]]


# if __name__ == "__main__":
#     # Quick manual smoke test
#     for dish in get_all_dishes():
#         print(f"{dish['id']:>2} | {dish['name']:<25} | {dish['cuisine']:<10} "
#               f"| ₹{dish['price']:<5} | ⭐{dish['rating']} | {dish['dietary_tags']}")
