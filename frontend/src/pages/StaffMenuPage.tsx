import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../AuthContext";
import { money } from "../format";
import type { MenuCategory, Restaurant, RestaurantMenu } from "../types";

const SELECTED_KEY = "takeaway-staff-restaurant";

export function StaffMenuPage() {
  const { user, loading: authLoading } = useAuth();
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [restaurantId, setRestaurantId] = useState(
    () => localStorage.getItem(SELECTED_KEY) ?? "",
  );
  const [menu, setMenu] = useState<RestaurantMenu | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [categoryName, setCategoryName] = useState("");
  const [itemForm, setItemForm] = useState({
    categoryId: "",
    name: "",
    description: "",
    price: "",
  });

  async function loadRestaurants() {
    const result = await api<Restaurant[]>("/staff/restaurants");
    setRestaurants(result);
    const selected =
      result.find((restaurant) => restaurant.id === restaurantId)?.id ??
      user?.restaurant_id ??
      result[0]?.id ??
      "";
    setRestaurantId(selected);
    if (selected) localStorage.setItem(SELECTED_KEY, selected);
  }

  async function loadMenu(id: string) {
    const result = await api<RestaurantMenu>(`/staff/restaurants/${id}/menu`);
    setMenu(result);
  }

  useEffect(() => {
    if (!user || (user.role !== "staff" && user.role !== "admin")) return;
    void loadRestaurants().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not load restaurants.");
    });
  }, [user]);

  useEffect(() => {
    if (!restaurantId) return;
    void loadMenu(restaurantId).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not load menu.");
    });
  }, [restaurantId]);

  async function addCategory(event: FormEvent) {
    event.preventDefault();
    if (!restaurantId || !categoryName.trim()) return;
    setError(null);
    try {
      await api(`/staff/restaurants/${restaurantId}/categories`, {
        method: "POST",
        body: JSON.stringify({ name: categoryName.trim(), sort_order: 0 }),
      });
      setCategoryName("");
      await loadMenu(restaurantId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create category.");
    }
  }

  async function addItem(event: FormEvent) {
    event.preventDefault();
    if (!itemForm.categoryId) return;
    setError(null);
    try {
      await api(`/staff/categories/${itemForm.categoryId}/items`, {
        method: "POST",
        body: JSON.stringify({
          name: itemForm.name,
          description: itemForm.description || null,
          price: itemForm.price,
          is_available: true,
        }),
      });
      setItemForm({ categoryId: itemForm.categoryId, name: "", description: "", price: "" });
      await loadMenu(restaurantId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create item.");
    }
  }

  async function toggleItem(itemId: string, isAvailable: boolean) {
    await api(`/staff/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_available: isAvailable }),
    });
    await loadMenu(restaurantId);
  }

  async function deleteItem(itemId: string) {
    await api(`/staff/items/${itemId}`, { method: "DELETE" });
    await loadMenu(restaurantId);
  }

  async function deleteCategory(category: MenuCategory) {
    if (category.items.length > 0) {
      setError("Remove or move menu items before deleting this category");
      return;
    }
    await api(`/staff/categories/${category.id}`, { method: "DELETE" });
    await loadMenu(restaurantId);
  }

  if (authLoading) return <p className="feedback">Loading…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: "/staff/menu" }} />;
  if (user.role !== "staff" && user.role !== "admin") return <Navigate to="/" replace />;

  return (
    <section className="content-section">
      <p className="eyebrow">STAFF</p>
      <h2>Menu manager</h2>
      {error && <p className="checkout-error">{error}</p>}
      {user.role === "admin" && restaurants.length > 1 && (
        <label className="staff-select">
          Restaurant
          <select
            value={restaurantId}
            onChange={(event) => {
              setRestaurantId(event.target.value);
              localStorage.setItem(SELECTED_KEY, event.target.value);
            }}
          >
            {restaurants.map((restaurant) => (
              <option key={restaurant.id} value={restaurant.id}>
                {restaurant.name}
              </option>
            ))}
          </select>
        </label>
      )}

      <form className="staff-form" onSubmit={(event) => void addCategory(event)}>
        <h3>New category</h3>
        <input
          value={categoryName}
          onChange={(event) => setCategoryName(event.target.value)}
          placeholder="Category name"
          required
        />
        <button className="secondary-button" type="submit">
          Add category
        </button>
      </form>

      <form className="staff-form" onSubmit={(event) => void addItem(event)}>
        <h3>New item</h3>
        <select
          value={itemForm.categoryId}
          onChange={(event) =>
            setItemForm((current) => ({ ...current, categoryId: event.target.value }))
          }
          required
        >
          <option value="">Choose category</option>
          {menu?.categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        <input
          value={itemForm.name}
          onChange={(event) =>
            setItemForm((current) => ({ ...current, name: event.target.value }))
          }
          placeholder="Item name"
          required
        />
        <input
          value={itemForm.description}
          onChange={(event) =>
            setItemForm((current) => ({ ...current, description: event.target.value }))
          }
          placeholder="Description"
        />
        <input
          value={itemForm.price}
          onChange={(event) =>
            setItemForm((current) => ({ ...current, price: event.target.value }))
          }
          placeholder="Price"
          required
        />
        <button className="secondary-button" type="submit">
          Add item
        </button>
      </form>

      {menu?.categories.map((category) => (
        <section className="menu-category" key={category.id}>
          <div className="staff-category-heading">
            <h2>{category.name}</h2>
            <button className="clear-cart" onClick={() => void deleteCategory(category)}>
              Delete category
            </button>
          </div>
          {category.items.map((item) => (
            <article className="menu-item" key={item.id}>
              <div className="menu-item-copy">
                <h3>{item.name}</h3>
                {item.description && <p>{item.description}</p>}
                <strong>{money.format(item.price)}</strong>
                {!item.is_available && <p>Hidden from customers</p>}
              </div>
              <div className="menu-item-actions">
                <button
                  className="add-to-cart"
                  onClick={() => void toggleItem(item.id, !item.is_available)}
                >
                  {item.is_available ? "Hide" : "Show"}
                </button>
                <button className="clear-cart" onClick={() => void deleteItem(item.id)}>
                  Delete
                </button>
              </div>
            </article>
          ))}
        </section>
      ))}
    </section>
  );
}
