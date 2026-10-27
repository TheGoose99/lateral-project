import { useCart } from "../CartContext";
import { money } from "../format";
import { CheckoutDialog } from "./CheckoutDialog";

export function CartPanel() {
  const {
    cart,
    cartOpen,
    checkoutOpen,
    setCartOpen,
    setCheckoutOpen,
    changeQuantity,
    clearCart,
  } = useCart();

  if (!cartOpen && !checkoutOpen) return null;

  const cartLines = Object.values(cart.items);
  const cartCount = cartLines.reduce((sum, line) => sum + line.quantity, 0);
  const cartTotal = cartLines.reduce(
    (sum, line) => sum + line.item.price * line.quantity,
    0,
  );

  return (
    <>
      {cartOpen && (
        <aside className="cart-panel" aria-label="Shopping cart">
          <div className="cart-panel-heading">
            <div>
              <p className="eyebrow">YOUR ORDER</p>
              <h2>
                Your cart <span>({cartCount})</span>
              </h2>
            </div>
            <button
              className="cart-close"
              onClick={() => setCartOpen(false)}
              aria-label="Close cart"
            >
              ×
            </button>
          </div>

          {cartLines.length === 0 ? (
            <div className="cart-empty">
              <span aria-hidden="true">✳</span>
              <p>Your cart is empty.</p>
              <small>Add something delicious from a restaurant menu.</small>
            </div>
          ) : (
            <>
              <div className="cart-lines">
                {cartLines.map(({ item, quantity }) => (
                  <div className="cart-line" key={item.id}>
                    <div className="cart-line-copy">
                      <strong>{item.name}</strong>
                      <span>{money.format(item.price * quantity)}</span>
                    </div>
                    <div className="quantity-control">
                      <button
                        onClick={() => changeQuantity(item.id, -1)}
                        aria-label={`Decrease ${item.name} quantity`}
                      >
                        −
                      </button>
                      <span>{quantity}</span>
                      <button
                        onClick={() => changeQuantity(item.id, 1)}
                        aria-label={`Increase ${item.name} quantity`}
                      >
                        +
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="cart-total">
                <span>Subtotal</span>
                <strong>{money.format(cartTotal)}</strong>
              </div>
              <p className="cart-note">
                Delivery fees, if applicable, are not included.
              </p>
              <button
                className="checkout-button"
                onClick={() => setCheckoutOpen(true)}
              >
                Continue to checkout <span aria-hidden="true">→</span>
              </button>
              <button className="clear-cart" onClick={clearCart}>
                Clear cart
              </button>
            </>
          )}
        </aside>
      )}
      {checkoutOpen && <CheckoutDialog />}
    </>
  );
}
