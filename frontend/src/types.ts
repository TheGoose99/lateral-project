export type User = {
  id: string;
  email: string;
  full_name: string;
  role: "customer" | "staff" | "admin";
  restaurant_id: string | null;
};

export type Restaurant = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  address: string;
  phone: string | null;
};

export type MenuItem = {
  id: string;
  name: string;
  description: string | null;
  price: number;
  is_available: boolean;
};

export type MenuCategory = {
  id: string;
  name: string;
  sort_order: number;
  items: MenuItem[];
};

export type RestaurantMenu = Restaurant & {
  categories: MenuCategory[];
};

export type CartLine = {
  item: MenuItem;
  quantity: number;
};

export type SavedCart = {
  restaurantId: string;
  items: Record<string, CartLine>;
};

export type OrderItem = {
  id: string;
  menu_item_id: string | null;
  name_snapshot: string;
  unit_price_snapshot: number | string;
  quantity: number;
  line_total: number | string;
};

export type StatusHistory = {
  from_status: string | null;
  to_status: string;
  reason: string | null;
  created_at: string;
};

export type Order = {
  id: string;
  restaurant_id: string;
  restaurant_name: string;
  status: string;
  total_amount: number | string;
  currency: string;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  status_history: StatusHistory[];
};

export type PaginatedOrders = {
  items: Order[];
  total: number;
  limit: number;
  offset: number;
};

export const CANCELLABLE_STATUSES = new Set(["pending", "accepted", "preparing"]);

export const STAFF_NEXT_STATUS: Record<string, { status: string; label: string }[]> = {
  pending: [{ status: "accepted", label: "Accept" }],
  accepted: [
    { status: "preparing", label: "Start preparing" },
    { status: "out_for_delivery", label: "Out for delivery" },
  ],
  preparing: [{ status: "out_for_delivery", label: "Out for delivery" }],
  out_for_delivery: [{ status: "delivered", label: "Mark delivered" }],
};
