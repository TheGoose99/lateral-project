"""Seed fictional demo restaurants, menus, and users. Safe to rerun."""
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import MenuCategory, MenuItem, Restaurant, User

DEMO_PASSWORD = "correct-horse-battery-staple"


RESTAURANTS = [
    {
        "name": "Bun & Bun",
        "slug": "bun-and-bun",
        "description": "Burgers made fresh, crispy sides, and proper comfort food.",
        "address": "Strada Franceză 12, București",
        "phone": "+40 721 000 101",
        "categories": [
            {
                "name": "Burgers",
                "items": [
                    (
                        "Classic Smash Burger",
                        "Double beef patty, cheddar, pickles, house sauce.",
                        "34.90",
                    ),
                    (
                        "BBQ Bacon Burger",
                        "Beef, smoked bacon, cheddar, BBQ sauce, crispy onions.",
                        "39.90",
                    ),
                    (
                        "Crispy Chicken Burger",
                        "Crispy chicken, lettuce, pickles, garlic mayo.",
                        "32.90",
                    ),
                    ("Veggie Burger", "Plant-based patty, tomato, lettuce, vegan sauce.", "31.90"),
                ],
            },
            {
                "name": "Sides",
                "items": [
                    ("Skin-on Fries", "Golden fries with sea salt.", "12.90"),
                    (
                        "Loaded Cheese Fries",
                        "Fries topped with cheddar sauce and spring onion.",
                        "19.90",
                    ),
                    ("Onion Rings", "Crispy battered onion rings.", "14.90"),
                ],
            },
            {
                "name": "Drinks",
                "items": [
                    ("Homemade Lemonade", "Fresh lemon, mint, and sparkling water.", "12.00"),
                    ("Cola", "330 ml.", "8.00"),
                ],
            },
        ],
    },
    {
        "name": "Casa Mămăligii",
        "slug": "casa-mamaligii",
        "description": "Romanian favourites, slow-cooked dishes, and the taste of home.",
        "address": "Calea Moșilor 88, București",
        "phone": "+40 721 000 102",
        "categories": [
            {
                "name": "Feluri principale",
                "items": [
                    (
                        "Sarmale cu mămăligă",
                        "Traditional cabbage rolls served with polenta and sour cream.",
                        "36.00",
                    ),
                    (
                        "Tochitură românească",
                        "Pork stew with polenta, egg, and grated cheese.",
                        "42.00",
                    ),
                    ("Șnițel de pui", "Chicken schnitzel with golden potatoes.", "34.00"),
                    ("Fasole cu ciolan", "Slow-cooked beans with smoked pork knuckle.", "39.00"),
                ],
            },
            {
                "name": "Supe și ciorbe",
                "items": [
                    ("Ciorbă de burtă", "Traditional tripe soup with sour cream.", "22.00"),
                    ("Ciorbă de legume", "Seasonal vegetable soup.", "17.00"),
                ],
            },
            {
                "name": "Desert",
                "items": [
                    ("Papanași", "Fried cheese doughnuts with sour cream and jam.", "24.00"),
                    ("Clătite cu dulceață", "Thin pancakes with homemade fruit jam.", "16.00"),
                ],
            },
        ],
    },
    {
        "name": "Verde Bowl",
        "slug": "verde-bowl",
        "description": "Fresh bowls, colourful salads, and feel-good everyday food.",
        "address": "Bulevardul Dacia 25, București",
        "phone": "+40 721 000 103",
        "categories": [
            {
                "name": "Bowls",
                "items": [
                    (
                        "Chicken Power Bowl",
                        "Grilled chicken, quinoa, avocado, greens, lemon dressing.",
                        "36.90",
                    ),
                    ("Mediterranean Bowl", "Falafel, hummus, cucumber, tomato, couscous.", "32.90"),
                    (
                        "Salmon Balance Bowl",
                        "Salmon, brown rice, edamame, cucumber, sesame.",
                        "44.90",
                    ),
                ],
            },
            {
                "name": "Salads",
                "items": [
                    ("Greek Salad", "Tomatoes, cucumber, feta, olives, red onion.", "29.90"),
                    (
                        "Caesar Salad",
                        "Romaine lettuce, parmesan, croutons, Caesar dressing.",
                        "31.90",
                    ),
                    (
                        "Green Garden Salad",
                        "Seasonal greens, avocado, seeds, citrus dressing.",
                        "27.90",
                    ),
                ],
            },
            {
                "name": "Drinks",
                "items": [
                    ("Fresh Orange Juice", "Freshly squeezed orange juice.", "14.00"),
                    ("Green Apple Smoothie", "Apple, spinach, banana, and lime.", "16.00"),
                ],
            },
        ],
    },
]


def seed() -> None:
    with SessionLocal.begin() as db:
        added_restaurants = 0
        added_categories = 0
        added_items = 0

        for restaurant_data in RESTAURANTS:
            restaurant = db.scalar(
                select(Restaurant).where(Restaurant.slug == restaurant_data["slug"])
            )

            if restaurant is None:
                restaurant = Restaurant(
                    name=restaurant_data["name"],
                    slug=restaurant_data["slug"],
                    description=restaurant_data["description"],
                    address=restaurant_data["address"],
                    phone=restaurant_data["phone"],
                    is_active=True,
                )
                db.add(restaurant)
                db.flush()
                added_restaurants += 1

            for category_order, category_data in enumerate(
                restaurant_data["categories"]
            ):
                category = db.scalar(
                    select(MenuCategory).where(
                        MenuCategory.restaurant_id == restaurant.id,
                        MenuCategory.name == category_data["name"],
                    )
                )

                if category is None:
                    category = MenuCategory(
                        restaurant_id=restaurant.id,
                        name=category_data["name"],
                        sort_order=category_order,
                    )
                    db.add(category)
                    db.flush()
                    added_categories += 1

                existing_items = set(
                    db.scalars(
                        select(MenuItem.name).where(
                            MenuItem.category_id == category.id
                        )
                    ).all()
                )

                for name, description, price in category_data["items"]:
                    if name in existing_items:
                        continue

                    db.add(
                        MenuItem(
                            category_id=category.id,
                            name=name,
                            description=description,
                            price=Decimal(price),
                            is_available=True,
                        )
                    )
                    added_items += 1

        bun_and_bun = db.scalar(select(Restaurant).where(Restaurant.slug == "bun-and-bun"))
        demo_users = [
            {
                "email": "customer@example.com",
                "full_name": "Demo Customer",
                "role": "customer",
                "restaurant_id": None,
            },
            {
                "email": "staff@example.com",
                "full_name": "Demo Staff",
                "role": "staff",
                "restaurant_id": bun_and_bun.id if bun_and_bun is not None else None,
            },
            {
                "email": "admin@example.com",
                "full_name": "Demo Admin",
                "role": "admin",
                "restaurant_id": None,
            },
        ]
        added_users = 0
        for user_data in demo_users:
            user = db.scalar(select(User).where(User.email == user_data["email"]))
            if user is None:
                db.add(
                    User(
                        email=user_data["email"],
                        password_hash=hash_password(DEMO_PASSWORD),
                        full_name=user_data["full_name"],
                        role=user_data["role"],
                        restaurant_id=user_data["restaurant_id"],
                        is_active=True,
                    )
                )
                added_users += 1
            else:
                user.role = user_data["role"]
                user.restaurant_id = user_data["restaurant_id"]
                user.is_active = True

        print(
            "Seed complete: "
            f"{added_restaurants} restaurants, "
            f"{added_categories} categories, "
            f"{added_items} menu items, "
            f"{added_users} users added."
        )
        print("Existing matching records were preserved.")
        print(
            "Demo logins (password: correct-horse-battery-staple): "
            "customer@example.com, staff@example.com, admin@example.com"
        )


if __name__ == "__main__":
    seed()
