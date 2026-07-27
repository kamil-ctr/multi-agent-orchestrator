import { createContext, useContext, useEffect, useState } from "react";

const SettingsContext = createContext(null);

const DEFAULT_SETTINGS = {
  disabledAgents: [], // agent names the user has manually turned off
  voiceAutoplay: false, // auto-speak the synthesized answer when it lands
  voiceRate: 1,
};

function loadSettings() {
  try {
    const raw = localStorage.getItem("mao_settings");
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : DEFAULT_SETTINGS;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(loadSettings);

  useEffect(() => {
    localStorage.setItem("mao_settings", JSON.stringify(settings));
  }, [settings]);

  const toggleAgent = (name) =>
    setSettings((s) => ({
      ...s,
      disabledAgents: s.disabledAgents.includes(name)
        ? s.disabledAgents.filter((n) => n !== name)
        : [...s.disabledAgents, name],
    }));

  const update = (patch) => setSettings((s) => ({ ...s, ...patch }));

  return (
    <SettingsContext.Provider value={{ settings, toggleAgent, update }}>{children}</SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}
