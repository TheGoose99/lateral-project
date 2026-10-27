import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../AuthContext";
import { formatStatus, money } from "../format";
import { CANCELLABLE_STATUSES, type Order } from "../types";

export function OrderDetailPage() {
  const { orderId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  async function load() {
    if (!orderId) return;
    try {
      const result = await api<Order>(`/orders/${orderId}`);
      setOrder(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this order.");
    }
  }

  useEffect(() => {
    if (!user || user.role !== "customer") return;
    void load();
  }, [user, orderId]);

  useEffect(() => {
    if (!order || order.status === "delivered" || order.status === "cancelled") {
      return;
    }
    const timer = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [order?.status, orderId]);

  async function cancelOrder() {
    if (!orderId || !reason.trim()) return;
    setCancelling(true);
    setError(null);
    try {
      const result = await api<Order>(`/orders/${orderId}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason: reason.trim() }),
      });
      setOrder(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel this order.");
    } finally {
      setCancelling(false);
    }
  }

  if (authLoading) return <p className="feedback">Loading…</p>;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: `/orders/${orderId}` }} />;
  }
  if (user.role !== "customer") return <Navigate to="/" replace />;

  return (
    <section className="content-section">
      <div className="breadcrumb" style={{ padding: 0, marginBottom: 24 }}>
        <Link to="/orders">My orders</Link>
        <span>/</span>
        <span>Order</span>
      </div>
      {error && <p className="checkout-error">{error}</p>}
      {order && (
        <>
          <p className="eyebrow">ORDER STATUS</p>
          <h2>{formatStatus(order.status)}</h2>
          <p>
            {order.restaurant_name} · {money.format(Number(order.total_amount))}
          </p>
          <ul className="order-items">
            {order.items.map((item) => (
              <li key={item.id}>
                {item.quantity} × {item.name_snapshot} —{" "}
                {money.format(Number(item.line_total))}
              </li>
            ))}
          </ul>
          <h3>History</h3>
          <ol className="status-history">
            {order.status_history.map((entry, index) => (
              <li key={`${entry.created_at}-${index}`}>
                <strong>{formatStatus(entry.to_status)}</strong>
                <span>{new Date(entry.created_at).toLocaleString()}</span>
                {entry.reason && <p>{entry.reason}</p>}
              </li>
            ))}
          </ol>
          {CANCELLABLE_STATUSES.has(order.status) && (
            <div className="cancel-box">
              <label>
                Cancel this order
                <input
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Reason"
                  maxLength={500}
                />
              </label>
              <button
                className="secondary-button"
                disabled={cancelling || !reason.trim()}
                onClick={() => void cancelOrder()}
              >
                {cancelling ? "Cancelling…" : "Cancel order"}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
