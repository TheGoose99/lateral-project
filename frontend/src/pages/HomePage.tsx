import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import type { Restaurant } from "../types";

export function HomePage() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    void api<Restaurant[]>("/restaurants")
      .then(setRestaurants)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">YOUR NEXT MEAL STARTS HERE</p>
          <h1>
            Good food.
            <br />
            <span>No fuss.</span>
          </h1>
          <p className="hero-description">
            Discover local restaurants, explore their menus, and find something
            worth looking forward to.
          </p>
          <a className="primary-link" href="#restaurants">
            Explore restaurants <span aria-hidden="true">↓</span>
          </a>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="art-circle circle-back" />
          <div className="art-circle circle-front">
            <span className="art-symbol">✳</span>
          </div>
          <div className="art-label">Made for your appetite.</div>
          <span className="art-spark spark-one">✳</span>
          <span className="art-spark spark-two">✦</span>
        </div>
      </section>

      <section id="restaurants" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">THE LOCAL LINEUP</p>
            <h2>Restaurants to explore</h2>
          </div>
          {!loading && !error && (
            <span className="result-count">
              {restaurants.length} {restaurants.length === 1 ? "place" : "places"}
            </span>
          )}
        </div>

        {loading && (
          <div className="feedback" role="status">
            <span className="spinner" />
            <p>Finding restaurants…</p>
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

        {!loading && !error && restaurants.length === 0 && (
          <div className="empty-state">
            <span className="empty-icon">✳</span>
            <h3>Your next favourite is on its way.</h3>
            <p>No restaurants are available yet. Check back soon.</p>
          </div>
        )}

        {!loading && !error && restaurants.length > 0 && (
          <div className="restaurant-grid">
            {restaurants.map((restaurant, index) => (
              <Link
                className="restaurant-card"
                key={restaurant.id}
                to={`/restaurants/${restaurant.id}`}
              >
                <div className={`restaurant-art art-${index % 4}`}>
                  <span className="restaurant-art-symbol">
                    {["✳", "✦", "❋", "✺"][index % 4]}
                  </span>
                  <span className="view-menu">
                    View menu <span>↗</span>
                  </span>
                </div>
                <div className="restaurant-card-copy">
                  <div className="restaurant-card-title">
                    <h3>{restaurant.name}</h3>
                    <span aria-hidden="true">→</span>
                  </div>
                  <p>{restaurant.description || "Good food, made with care."}</p>
                  <span className="restaurant-address">{restaurant.address}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
