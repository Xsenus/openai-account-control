import React, { useState } from "react";

type Props = {
  onLogin: (credentials: { username: string; password: string }) => Promise<void>;
};

export function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      await onLogin({ username: username.trim(), password });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить вход.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-layout">
        <section className="login-copy">
          <p className="eyebrow">Self-hosted access</p>
          <h1>Вход в панель управления</h1>
          <p className="login-lead">
            Панель закрыта авторизацией оператора. Bootstrap-доступ задается в <code>.env</code>, а обычное управление
            пользователями теперь выполняется прямо из раздела настроек.
          </p>

          <div className="login-benefits">
            <article className="panel feature-card">
              <h3>Единый защищенный вход</h3>
              <p className="muted">API, evidence-артефакты и рабочий интерфейс доступны только после авторизации.</p>
            </article>
            <article className="panel feature-card">
              <h3>Локальное хранение данных</h3>
              <p className="muted">Сессии OpenAI остаются у вас, пароли OpenAI в проекте не сохраняются.</p>
            </article>
            <article className="panel feature-card">
              <h3>Рабочий UX под оператора</h3>
              <p className="muted">Список учеток, операции входа, scan и настройка порогов собраны в одном потоке.</p>
            </article>
          </div>
        </section>

        <section className="panel login-card">
          <p className="eyebrow">Operator login</p>
          <h2>Откройте рабочую панель</h2>
          <p className="muted">Если меняли доступ, проверьте значения в <code>.env</code> и перезапустите backend.</p>

          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="field">
              <span>Логин</span>
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="admin"
                required
              />
            </label>

            <label className="field">
              <span>Пароль</span>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Введите пароль панели"
                required
              />
            </label>

            {error ? <div className="alert error">{error}</div> : null}

            <button type="submit" className="primary-button" disabled={busy}>
              {busy ? "Выполняю вход..." : "Войти"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
