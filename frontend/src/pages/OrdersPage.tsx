import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../AuthContext";
import { formatStatus, money } from "../format";
import type { PaginatedOrders } from "../types";

export function OrdersPage() {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState<PaginatedOrders | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || user.role !== "customer") return;
    void api<PaginatedOrders>("/orders")
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load orders.");
      });
  }, [user]);

  if (authLoading) return <p className="feedback">Loading…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: "/orders" }} />;
  if (user.role !== "customer") return <Navigate to="/" replace />;

  return (
    <section className="content-section">
      <p className="eyebrow">YOUR ORDERS</p>
      <h2>My orders</h2>
      {error && <p className="checkout-error">{error}</p>}
      {data && data.items.length === 0 && (
        <div className="empty-state">
          <h3>No orders yet.</h3>
          <p>Browse a restaurant and check out when you're ready.</p>
        </div>
      )}
      {data && data.items.length > 0 && (
        <div className="order-list">
          {data.items.map((order) => (
            <Link className="order-row" key={order.id} to={`/orders/${order.id}`}>
              <div>
                <strong>{formatStatus(order.status)}</strong>
                <p>
                  {order.restaurant_name} · {new Date(order.created_at).toLocaleString()}
                </p>
              </div>
              <span>{money.format(Number(order.total_amount))}</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
