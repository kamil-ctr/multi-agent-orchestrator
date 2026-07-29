import { NavLink, Outlet } from "react-router-dom";
import { motion } from "framer-motion";
import { MessageSquare, Trophy, Settings, Sun, Moon, Bot } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

const navItems = [
  { to: "/", label: "Chat", icon: MessageSquare, end: true },
  { to: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { to: "/settings", label: "Settings", icon: Settings },
];

/**
 * App shell: top nav bar (logo, Chat/Leaderboard/Settings tabs, theme
 * toggle) plus a react-router `<Outlet />` for the active page.
 *
 * Takes no props — reads/writes theme via useTheme and renders whichever
 * route matched in App.jsx's <Routes>.
 *
 * @returns {JSX.Element}
 */
export default function Layout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex h-screen flex-col" style={{ background: "var(--surface-0)" }}>
      <header
        className="flex shrink-0 items-center justify-between border-b px-4 py-2.5 shadow-[var(--shadow-sm)]"
        style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
      >
        <div className="flex items-center gap-2 font-semibold" style={{ color: "var(--text-primary)" }}>
          <span
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
          >
            <Bot size={17} />
          </span>
          <span className="hidden sm:inline">Multi-Agent Orchestrator</span>
        </div>

        <nav className="flex items-center gap-1 rounded-lg p-1" style={{ background: "var(--surface-2)" }}>
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `relative flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive ? "" : "hover:opacity-80"
                }`
              }
              style={({ isActive }) => ({ color: isActive ? "var(--accent-contrast)" : "var(--text-secondary)" })}
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className="absolute inset-0 rounded-md"
                      style={{ background: "var(--accent)" }}
                      transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    />
                  )}
                  <Icon size={15} className="relative" />
                  <span className="relative hidden md:inline">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="flex h-8 w-8 items-center justify-center rounded-md transition-colors hover:opacity-80"
          style={{ background: "var(--surface-2)", color: "var(--text-secondary)" }}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </header>

      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
