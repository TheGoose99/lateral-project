import { useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../AuthContext";
import { formatStatus, money } from "../format";
import {
  CANCELLABLE_STATUSES,
  STAFF_NEXT_STATUS,
  type Order,
  type PaginatedOrders,
} from "../types";

const STATUS_FILTERS = [
  "all",
  "pending",
  "accepted",
  "preparing",
  "out_for_delivery",
  "delivered",
  "cancelled",
];

export function StaffQueuePage() {
  const { user, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState<Record<string, string>>({});

  async function load() {
    const result = await api<PaginatedOrders>("/orders/staff/queue?limit=100");
    setOrders(result.items);
  }

  useEffect(() => {
    if (!user || (user.role !== "staff" && user.role !== "admin")) return;
    void load().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not load the queue.");
    });
    const timer = window.setInterval(() => {
      void load().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [user]);

  async function updateStatus(orderId: string, status: string, cancelReason?: string) {
    setError(null);
    try {
      await api(`/orders/${orderId}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status,
          reason: cancelReason,
        }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the order.");
    }
  }

  const visible = useMemo(
    () => (filter === "all" ? orders : orders.filter((order) => order.status === filter)),
    [filter, orders],
  );

  if (authLoading) return <p className="feedback">Loading…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: "/staff" }} />;
  if (user.role !== "staff" && user.role !== "admin") return <Navigate to="/" replace />;

  return (
    <section className="content-section">
      <p className="eyebrow">STAFF</p>
      <h2>Order queue</h2>
      {error && <p className="checkout-error">{error}</p>}
      <div className="status-filters" role="tablist" aria-label="Filter orders by status">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            className={filter === status ? "filter-chip active" : "filter-chip"}
            onClick={() => setFilter(status)}
          >
            {status === "all" ? "All" : formatStatus(status)}
          </button>
        ))}
      </div>
      {visible.length === 0 && <p>No orders in this view yet.</p>}
      <div className="staff-queue">
        {visible.map((order) => (
          <article className="staff-order" key={order.id}>
            <header>
              <strong>{formatStatus(order.status)}</strong>
              <span>{money.format(Number(order.total_amount))}</span>
            </header>
            <p>
              {order.restaurant_name} · {new Date(order.created_at).toLocaleString()}
            </p>
            <ul>
              {order.items.map((item) => (
                <li key={item.id}>
                  {item.quantity} × {item.name_snapshot}
                </li>
              ))}
            </ul>
            {(STAFF_NEXT_STATUS[order.status] ?? []).length > 0 && (
              <div className="staff-actions">
                {(STAFF_NEXT_STATUS[order.status] ?? []).map((action) => (
                  <button
                    key={action.status}
                    className="secondary-button"
                    onClick={() => void updateStatus(order.id, action.status)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
            {CANCELLABLE_STATUSES.has(order.status) && (
              <div className="cancel-box">
                <input
                  value={reason[order.id] ?? ""}
                  onChange={(event) =>
                    setReason((current) => ({
                      ...current,
                      [order.id]: event.target.value,
                    }))
                  }
                  placeholder="Cancellation reason"
                />
                <button
                  className="clear-cart"
                  disabled={!reason[order.id]?.trim()}
                  onClick={() =>
                    void updateStatus(order.id, "cancelled", reason[order.id].trim())
                  }
                >
                  Cancel order
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
