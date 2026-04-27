import React, { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { api, setUnauthorizedHandler } from "./api/client";
import { Layout } from "./components/Layout";
import { AccountsPage } from "./pages/AccountsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { SettingsPage } from "./pages/SettingsPage";
import type { AuthSession } from "./types";

function loggedOutSession(): AuthSession {
  return {
    auth_enabled: true,
    authenticated: false,
    user_id: null,
    username: null,
    issued_at: null,
    expires_at: null
  };
}

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSession() {
    setLoading(true);
    setError("");
    try {
      const nextSession = await api.getAuthSession();
      setSession(nextSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось подключиться к backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSession();
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession((current) => {
        if (!current?.auth_enabled) {
          return current ?? loggedOutSession();
        }
        return loggedOutSession();
      });
    });

    return () => {
      setUnauthorizedHandler(null);
    };
  }, []);

  async function handleLogin(credentials: { username: string; password: string }) {
    const nextSession = await api.login(credentials);
    setSession(nextSession);
  }

  async function handleLogout() {
    const nextSession = await api.logout();
    setSession(nextSession);
  }

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-card panel">
          <p className="eyebrow">Control Center</p>
          <h1>Подключение к панели</h1>
          <div className="loading-state">
            <div className="loading-spinner" aria-hidden="true" />
            <p className="muted">Проверяем backend и статус сессии оператора.</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-loading">
        <div className="loading-card panel">
          <p className="eyebrow">Control Center</p>
          <h1>Backend недоступен</h1>
          <p className="muted">{error}</p>
          <button className="primary-button" onClick={() => void loadSession()}>
            Повторить
          </button>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  if (session.auth_enabled && !session.authenticated) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <Layout session={session} onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/accounts" element={<AccountsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage session={session} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
