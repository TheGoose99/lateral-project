import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { useCart } from "../CartContext";
import { money } from "../format";
import type { RestaurantMenu } from "../types";

export function RestaurantPage() {
  const { restaurantId } = useParams();
  const { addToCart } = useCart();
  const [menu, setMenu] = useState<RestaurantMenu | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!restaurantId) return;
    setLoading(true);
    setError(null);
    void api<RestaurantMenu>(`/restaurants/${restaurantId}/menu`)
      .then(setMenu)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, [restaurantId]);

  const itemCount =
    menu?.categories.reduce((total, category) => total + category.items.length, 0) ?? 0;

  return (
    <>
      <div className="breadcrumb">
        <Link to="/">Restaurants</Link>
        <span>/</span>
        <span>{menu?.name ?? "Menu"}</span>
      </div>

      {menu && !loading && !error && (
        <section className="menu-heading">
          <p className="eyebrow">EXPLORE THE MENU</p>
          <h1>{menu.name}</h1>
          {menu.description && <p>{menu.description}</p>}
          <div className="restaurant-meta">
            <span>
              <span aria-hidden="true">⌖</span> {menu.address}
            </span>
            {menu.phone && <span>{menu.phone}</span>}
          </div>
        </section>
      )}

      <section className="content-section">
        {loading && (
          <div className="feedback" role="status">
            <span className="spinner" />
            <p>Loading the menu…</p>
          </div>
        )}

        {error && !loading && (
          <div className="feedback error-panel" role="alert">
            <span className="feedback-icon">!</span>
            <h3>We couldn't load that just yet.</h3>
            <p>{error}</p>
            <button className="secondary-button" onClick={load}>
              Try again
            </button>
          </div>
        )}

        {!loading && !error && menu &&
          (itemCount === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">✳</span>
              <h3>The menu is being prepared.</h3>
              <p>There are no available items at this restaurant right now.</p>
            </div>
          ) : (
            <div className="menu-layout">
              <nav className="category-nav" aria-label="Menu categories">
                {menu.categories
                  .filter((category) => category.items.length > 0)
                  .map((category) => (
                    <a key={category.id} href={`#category-${category.id}`}>
                      {category.name}
                    </a>
                  ))}
              </nav>

              <div className="menu-content">
                {menu.categories
                  .filter((category) => category.items.length > 0)
                  .map((category) => (
                    <section
                      className="menu-category"
                      id={`category-${category.id}`}
                      key={category.id}
                    >
                      <h2>{category.name}</h2>
                      <div className="menu-items">
                        {category.items.map((item) => (
                          <article className="menu-item" key={item.id}>
                            <div className="menu-item-copy">
                              <h3>{item.name}</h3>
                              {item.description && <p>{item.description}</p>}
                              <strong>{money.format(item.price)}</strong>
                            </div>
                            <div className="menu-item-actions">
                              <div className="menu-item-art" aria-hidden="true">
                                ✳
                              </div>
                              <button
                                className="add-to-cart"
                                disabled={!item.is_available}
                                onClick={() => addToCart(item, menu.id)}
                              >
                                {item.is_available ? "+ Add" : "Unavailable"}
                              </button>
                            </div>
                          </article>
                        ))}
                      </div>
                    </section>
                  ))}
              </div>
            </div>
          ))}
      </section>
    </>
  );
}
