import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../AuthContext";
import { useCart } from "../CartContext";

export function Header() {
  const { user, logout } = useAuth();
  const { cart, setCartOpen, cartOpen } = useCart();
  const cartCount = Object.values(cart.items).reduce(
    (sum, line) => sum + line.quantity,
    0,
  );
  const isStaff = user?.role === "staff" || user?.role === "admin";

  return (
    <header className="topbar">
      <Link className="brand" to="/" aria-label="Takeaway home">
        <span className="brand-mark">t.</span>
        <span>takeaway</span>
      </Link>

      <nav className="topbar-right" aria-label="Main">
        {user?.role === "customer" && (
          <NavLink className="nav-link" to="/orders">
            My orders
          </NavLink>
        )}
        {isStaff && (
          <>
            <NavLink className="nav-link" to="/staff" end>
              Staff queue
            </NavLink>
            <NavLink className="nav-link" to="/staff/menu">
              Menu
            </NavLink>
          </>
        )}
        {user ? (
          <button className="nav-link nav-button" onClick={logout}>
            Sign out
          </button>
        ) : (
          <NavLink className="nav-link" to="/login">
            Sign in
          </NavLink>
        )}
        <button
          className="cart-trigger"
          onClick={() => setCartOpen(!cartOpen)}
          aria-expanded={cartOpen}
        >
          <span aria-hidden="true">▣</span> Cart
          <span className="cart-badge">{cartCount}</span>
        </button>
      </nav>
    </header>
  );
}
