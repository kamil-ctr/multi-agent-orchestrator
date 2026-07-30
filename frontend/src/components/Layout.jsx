import { NavLink, Outlet } from "react-router-dom";
import { MessageSquare, Trophy, Settings } from "lucide-react";

const navItems = [
  { to: "/", label: "Chat", icon: MessageSquare, end: true },
  { to: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { to: "/settings", label: "Settings", icon: Settings },
];

/**
 * App shell: top nav bar (wordmark, Chat/Leaderboard/Settings tabs) plus a
 * react-router `<Outlet />` for the active page.
 *
 * Chrome carries no fill and no border — identity is opacity (active vs
 * inactive) on plain text/icons over the obsidian canvas, not a colored
 * pill. Dark is the only theme now, so there's no toggle here anymore.
 *
 * @returns {JSX.Element}
 */
export default function Layout() {
  return (
    <div className="flex h-screen flex-col" style={{ background: "var(--surface-0)" }}>
      <header className="flex shrink-0 items-center justify-between px-4 py-3" style={{ background: "var(--surface-0)" }}>
        <span
          className="text-2xs uppercase"
          style={{ color: "var(--text-muted)", letterSpacing: "var(--tracking-label)" }}
        >
          Orchestrator
        </span>

        <nav className="flex items-center gap-6">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-1.5 text-2xs uppercase no-underline ${isActive ? "opacity-100" : "opacity-60"}`
              }
              style={{ color: "var(--text-primary)", letterSpacing: "var(--tracking-label)" }}
            >
              <Icon size={14} />
              <span className="hidden sm:inline">{label}</span>
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
