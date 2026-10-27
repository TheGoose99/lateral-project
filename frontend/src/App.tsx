import { Navigate, Route, Routes } from "react-router-dom";

import { CartPanel } from "./components/CartPanel";
import { Header } from "./components/Header";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { OrderDetailPage } from "./pages/OrderDetailPage";
import { OrdersPage } from "./pages/OrdersPage";
import { RestaurantPage } from "./pages/RestaurantPage";
import { StaffMenuPage } from "./pages/StaffMenuPage";
import { StaffQueuePage } from "./pages/StaffQueuePage";

export default function App() {
  return (
    <div className="app-shell">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/restaurants/:restaurantId" element={<RestaurantPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/:orderId" element={<OrderDetailPage />} />
          <Route path="/staff" element={<StaffQueuePage />} />
          <Route path="/staff/menu" element={<StaffMenuPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <CartPanel />
      <footer className="site-footer">
        <span className="footer-brand">
          <span className="brand-mark">t.</span> takeaway
        </span>
        <span>Good food brings us together.</span>
        <span>Made with care · Romania</span>
      </footer>
    </div>
  );
}
