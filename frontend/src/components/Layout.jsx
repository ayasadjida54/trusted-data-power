import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import Logo from "./Logo";
import { listAlerts } from "../api/client";

const NAV_ITEMS = [
  { to: "/", label: "Datasets", end: true },
  { to: "/upload", label: "Upload" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    listAlerts(true)
      .then((alerts) => setUnreadCount(alerts.length))
      .catch(() => {
        /* non-fatal - badge just stays at 0 */
      });
  }, []);

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col bg-navy px-4 py-6 text-white">
        <div className="mb-8 flex items-center gap-2 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10">
            <Logo size={20} />
          </div>
          <span className="text-sm font-semibold leading-tight">
            Trusted
            <br />
            Data Power
          </span>
        </div>

        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
          <NavLink
            to="/alerts"
            className={({ isActive }) =>
              `flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                isActive ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <span>Alerts</span>
            {unreadCount > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-cyan px-1.5 text-xs font-semibold text-navy">
                {unreadCount}
              </span>
            )}
          </NavLink>
        </nav>

        <div className="mt-auto space-y-3 px-2">
          {user && (
            <div className="border-t border-white/10 pt-3">
              <div className="truncate text-xs font-medium text-white/80">
                {user.organization.name}
              </div>
              <div className="truncate text-xs text-white/40">{user.email}</div>
              <button
                onClick={logout}
                className="mt-2 text-xs font-medium text-white/50 hover:text-white"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      <main className="flex-1 bg-surface">
        <Outlet />
      </main>
    </div>
  );
}
