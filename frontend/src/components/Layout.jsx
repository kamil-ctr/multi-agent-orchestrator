import { NavLink, Outlet } from "react-router-dom";
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
        className="flex shrink-0 items-center justify-between border-b px-4 py-2.5"
        style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
      >
        <div className="flex items-center gap-2 font-semibold" style={{ color: "var(--text-primary)" }}>
          <Bot size={22} className="text-blue-500" />
          <span className="hidden sm:inline">Multi-Agent Orchestrator</span>
        </div>

        <nav className="flex items-center gap-1 rounded-lg p-1" style={{ background: "var(--surface-2)" }}>
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive ? "text-white" : "hover:opacity-80"
                }`
              }
              style={({ isActive }) => ({
                background: isActive ? "#2a78d6" : "transparent",
                color: isActive ? "#fff" : "var(--text-secondary)",
              })}
            >
              <Icon size={15} />
              <span className="hidden md:inline">{label}</span>
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
