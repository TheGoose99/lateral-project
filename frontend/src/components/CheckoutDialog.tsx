import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../AuthContext";
import { useCart } from "../CartContext";
import { money } from "../format";
import type { Order } from "../types";

export function CheckoutDialog() {
  const navigate = useNavigate();
  const { user, login, register, logout } = useAuth();
  const { cart, setCheckoutOpen, setCartOpen, clearCart } = useCart();
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [placedOrder, setPlacedOrder] = useState<Order | null>(null);

  const cartLines = Object.values(cart.items);
  const cartCount = cartLines.reduce((sum, line) => sum + line.quantity, 0);
  const cartTotal = cartLines.reduce(
    (sum, line) => sum + line.item.price * line.quantity,
    0,
  );

  async function submitCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || !cart.restaurantId || cartLines.length === 0) return;
    setSubmitting(true);
    setError(null);

    try {
      if (!user) {
        if (authMode === "register") {
          await register(fullName, email, password);
        } else {
          await login(email, password);
        }
      }

      const idempotencyStorageKey = "takeaway-checkout-idempotency";
      let idempotencyKey = sessionStorage.getItem(idempotencyStorageKey);
      if (!idempotencyKey) {
        idempotencyKey = crypto.randomUUID();
        sessionStorage.setItem(idempotencyStorageKey, idempotencyKey);
      }

      const order = await api<Order>("/orders", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({
          restaurant_id: cart.restaurantId,
          items: cartLines.map(({ item, quantity }) => ({
            menu_item_id: item.id,
            quantity,
          })),
        }),
      });

      sessionStorage.removeItem(idempotencyStorageKey);
      setPlacedOrder(order);
      clearCart();
      setCartOpen(false);
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not place your order.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="checkout-overlay" role="presentation">
      <section
        className="checkout-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="checkout-title"
      >
        <button
          className="cart-close checkout-dismiss"
          onClick={() => setCheckoutOpen(false)}
          aria-label="Close checkout"
        >
          ×
        </button>

        {placedOrder ? (
          <div className="order-success">
            <span className="order-success-icon" aria-hidden="true">
              ✓
            </span>
            <p className="eyebrow">ORDER CONFIRMED</p>
            <h2 id="checkout-title">You're all set.</h2>
            <p>Your order has been submitted successfully.</p>
            <div className="order-reference">
              <span>Order reference</span>
              <strong>{placedOrder.id}</strong>
            </div>
            <div className="order-reference">
              <span>Status</span>
              <strong>{placedOrder.status}</strong>
            </div>
            <div className="order-reference">
              <span>Order total</span>
              <strong>{money.format(Number(placedOrder.total_amount))}</strong>
            </div>
            <button
              className="checkout-button"
              onClick={() => {
                setCheckoutOpen(false);
                navigate(`/orders/${placedOrder.id}`);
              }}
            >
              Track this order <span>→</span>
            </button>
          </div>
        ) : (
          <>
            <p className="eyebrow">ALMOST THERE</p>
            <h2 id="checkout-title">
              {user
                ? "Confirm your order"
                : authMode === "login"
                  ? "Log in to order"
                  : "Create your account"}
            </h2>
            <p className="checkout-intro">
              {user
                ? `Signed in as ${user.email}. Submit your order when you're ready.`
                : "Sign in or create an account to place your order."}
            </p>

            {!user && (
              <div className="auth-tabs">
                <button
                  type="button"
                  className={authMode === "login" ? "active" : ""}
                  onClick={() => {
                    setAuthMode("login");
                    setError(null);
                  }}
                >
                  Log in
                </button>
                <button
                  type="button"
                  className={authMode === "register" ? "active" : ""}
                  onClick={() => {
                    setAuthMode("register");
                    setError(null);
                  }}
                >
                  Create account
                </button>
              </div>
            )}

            <form className="checkout-form" onSubmit={submitCheckout}>
              {!user && authMode === "register" && (
                <label>
                  Full name
                  <input
                    autoComplete="name"
                    required
                    minLength={2}
                    maxLength={150}
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                  />
                </label>
              )}

              {!user && (
                <>
                  <label>
                    Email address
                    <input
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                    />
                  </label>
                  <label>
                    Password
                    <input
                      type="password"
                      autoComplete={
                        authMode === "register" ? "new-password" : "current-password"
                      }
                      required
                      minLength={authMode === "register" ? 12 : 1}
                      maxLength={128}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                    />
                    {authMode === "register" && <small>At least 12 characters.</small>}
                  </label>
                </>
              )}

              <div className="checkout-order-summary">
                <span>
                  {cartCount} {cartCount === 1 ? "item" : "items"}
                </span>
                <strong>{money.format(cartTotal)}</strong>
              </div>

              {error && (
                <p className="checkout-error" role="alert">
                  {error}
                </p>
              )}

              <button
                className="checkout-button"
                type="submit"
                disabled={submitting || cartLines.length === 0}
              >
                {submitting
                  ? "Processing…"
                  : user
                    ? "Place order"
                    : authMode === "register"
                      ? "Create account & order"
                      : "Log in & order"}
                {!submitting && <span aria-hidden="true">→</span>}
              </button>
            </form>

            {user && (
              <button
                className="clear-cart"
                onClick={() => {
                  logout();
                  setError(null);
                }}
              >
                Sign out / use another account
              </button>
            )}
          </>
        )}
      </section>
    </div>
  );
}
