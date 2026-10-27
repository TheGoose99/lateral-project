import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { MenuItem, SavedCart } from "./types";

const CART_KEY = "takeaway-cart";

const emptyCart: SavedCart = { restaurantId: "", items: {} };

function readCart(): SavedCart {
  try {
    const saved = localStorage.getItem(CART_KEY);
    return saved ? (JSON.parse(saved) as SavedCart) : emptyCart;
  } catch {
    return emptyCart;
  }
}

type CartContextValue = {
  cart: SavedCart;
  cartOpen: boolean;
  checkoutOpen: boolean;
  setCartOpen: (open: boolean) => void;
  setCheckoutOpen: (open: boolean) => void;
  addToCart: (item: MenuItem, restaurantId: string) => void;
  changeQuantity: (itemId: string, delta: number) => void;
  clearCart: () => void;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<SavedCart>(readCart);
  const [cartOpen, setCartOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  }, [cart]);

  const addToCart = useCallback((item: MenuItem, restaurantId: string) => {
    setCart((current) => {
      const count = Object.values(current.items).reduce(
        (sum, line) => sum + line.quantity,
        0,
      );
      if (current.restaurantId && current.restaurantId !== restaurantId && count > 0) {
        const confirmed = window.confirm(
          "Your cart contains items from another restaurant. Clear it and start a new order?",
        );
        if (!confirmed) return current;
        return {
          restaurantId,
          items: { [item.id]: { item, quantity: 1 } },
        };
      }
      return {
        restaurantId,
        items: {
          ...current.items,
          [item.id]: {
            item,
            quantity: (current.items[item.id]?.quantity ?? 0) + 1,
          },
        },
      };
    });
    setCartOpen(true);
  }, []);

  const changeQuantity = useCallback((itemId: string, delta: number) => {
    setCart((current) => {
      const line = current.items[itemId];
      if (!line) return current;
      const quantity = line.quantity + delta;
      const items = { ...current.items };
      if (quantity <= 0) delete items[itemId];
      else items[itemId] = { ...line, quantity };
      return {
        restaurantId: Object.keys(items).length ? current.restaurantId : "",
        items,
      };
    });
  }, []);

  const clearCart = useCallback(() => setCart(emptyCart), []);

  const value = useMemo(
    () => ({
      cart,
      cartOpen,
      checkoutOpen,
      setCartOpen,
      setCheckoutOpen,
      addToCart,
      changeQuantity,
      clearCart,
    }),
    [cart, cartOpen, checkoutOpen, addToCart, changeQuantity, clearCart],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used within CartProvider");
  return context;
}
