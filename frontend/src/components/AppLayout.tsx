/**
 * AppLayout — the persistent shell (sidebar + topbar) wrapping every
 * authenticated page. Visually consistent with the landing page's
 * "platform preview" mock, but every nav item here is a real route
 * (no locked/blurred items — that treatment was marketing-only).
 */
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import "./AppLayout.css";

const NAV_SECTIONS = [
  {
    label: "Overview",
    items: [
      { to: "/", label: "Dashboard", icon: "▦" },
      { to: "/signals", label: "Signal Library", icon: "◈" },
      { to: "/alerts", label: "Alerts", icon: "◉" },
    ],
  },
  {
    label: "Account",
    items: [{ to: "/settings", label: "Settings", icon: "⚙" }],
  },
];

export function AppLayout() {
  const { logout } = useAuth();

  return (
    <div className="shell">
      <div className="topbar">
        <div className="topbar-logo">GridSuite</div>
        <div className="topbar-right">
          <button className="tb-btn" onClick={logout}>
            Log out
          </button>
        </div>
      </div>

      <div className="main-layout">
        <nav className="sidebar">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="sidebar-section">
              <div className="sidebar-label">{section.label}</div>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                  end={item.to === "/"}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
