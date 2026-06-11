import {
  Bell,
  History,
  Key,
  LayoutDashboard,
  LogOut,
  Settings,
  Shield,
  ShieldCheck,
} from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { clearAuthToken } from "../api/client";

const navigation = [
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/live", label: "Live Interception", icon: Shield },
  { to: "/traces", label: "Trace Explorer", icon: History },
  { to: "/admin", label: "Guard Admin", icon: ShieldCheck },
  { to: "/tokens", label: "API Tokens", icon: Key },
];

function pageTitle(pathname: string) {
  if (pathname.startsWith("/live")) return "Live Interception";
  if (pathname.startsWith("/traces")) return "Trace Explorer";
  if (pathname.startsWith("/admin")) return "Guard Admin";
  if (pathname.startsWith("/tokens")) return "API Tokens";
  return "Overview";
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();

  function handleLogout() {
    clearAuthToken();
    navigate("/login");
  }

  const email = window.localStorage.getItem("agentguard.email") ?? "";
  const initials = email ? email[0].toUpperCase() : "OP";

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="wordmark">
          <div className="wordmark-icon">
            <Shield size={18} fill="currentColor" />
          </div>
          <div>
            <div className="wordmark-name">AgentGuard</div>
            <div className="wordmark-subtitle">AI Governance</div>
          </div>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `nav-item ${
                  isActive ||
                  (to === "/traces" && location.pathname.startsWith("/traces/"))
                    ? "nav-item-active"
                    : ""
                }`
              }
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <h1>{pageTitle(location.pathname)}</h1>
          <div className="topbar-actions">
            <button aria-label="Notifications" className="icon-button" type="button">
              <Bell size={19} />
            </button>
            <button aria-label="Settings" className="icon-button" type="button">
              <Settings size={19} />
            </button>
            <button
              aria-label="Sign out"
              className="icon-button"
              type="button"
              onClick={handleLogout}
              title={`Sign out (${email})`}
            >
              <LogOut size={19} />
            </button>
            <div className="avatar" aria-label="Operator profile" title={email}>
              {initials}
            </div>
          </div>
        </header>
        <main className="workspace">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
