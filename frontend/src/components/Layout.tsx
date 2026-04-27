import React from "react";
import { NavLink } from "react-router-dom";

import type { AuthSession } from "../types";

type Props = {
  children: React.ReactNode;
  session: AuthSession;
  onLogout: () => Promise<void>;
};

const NAV_ITEMS = [
  {
    to: "/",
    icon: "DB",
    label: "Дашборд",
    hint: "Общий статус, риски и последние проверки"
  },
  {
    to: "/accounts",
    icon: "AC",
    label: "Учетки",
    hint: "Реестр логинов, сессий и ручных операций"
  },
  {
    to: "/history",
    icon: "HI",
    label: "История",
    hint: "Очередь и результаты scan jobs"
  },
  {
    to: "/settings",
    icon: "ST",
    label: "Настройки",
    hint: "Пороги мониторинга и режимы проверки"
  }
];

export function Layout({ children, session, onLogout }: Props) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">OC</div>
          <div>
            <div className="brand">OpenAI Control Center</div>
            <p className="brand-subtitle">Self-hosted панель для нескольких OpenAI / ChatGPT-аккаунтов.</p>
          </div>
        </div>

        <nav className="nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              to={item.to}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>
                <span className="nav-label">{item.label}</span>
                <span className="nav-hint">{item.hint}</span>
              </span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="workspace-shell">
        <header className="topbar">
          <div className="topbar-copy">
            <p className="eyebrow">Operations panel</p>
            <p className="topbar-title">Account Control Center</p>
            <p className="muted">Мониторинг Codex-лимитов, сессий и рабочих аккаунтов в одном интерфейсе.</p>
          </div>

          <div className="topbar-actions">
            <div className="session-pill">
              <span className="muted">{session.auth_enabled ? "Вошли как" : "Режим доступа"}</span>
              <strong>{session.auth_enabled ? session.username ?? "оператор" : "без авторизации"}</strong>
            </div>
            {session.auth_enabled ? (
              <button className="ghost-button" onClick={() => void onLogout()}>
                Выйти
              </button>
            ) : null}
          </div>
        </header>

        <main className="content">{children}</main>
      </div>
    </div>
  );
}
