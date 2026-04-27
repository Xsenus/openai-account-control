import React, { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { Modal } from "../components/Modal";
import { OperatorEditorModal } from "../components/OperatorEditorModal";
import type { AuthSession, PanelUser, RuntimeSettings } from "../types";

type Props = {
  session: AuthSession;
};

type PasswordForm = {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
};

export function SettingsPage({ session }: Props) {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [users, setUsers] = useState<PanelUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [settingsBusy, setSettingsBusy] = useState(false);
  const [accessBusy, setAccessBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [settingsError, setSettingsError] = useState("");
  const [settingsSuccess, setSettingsSuccess] = useState("");
  const [accessError, setAccessError] = useState("");
  const [accessSuccess, setAccessSuccess] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [createOperatorOpen, setCreateOperatorOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [tipsOpen, setTipsOpen] = useState(false);
  const [passwordForm, setPasswordForm] = useState<PasswordForm>({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });

  async function load() {
    setLoading(true);
    setSettingsError("");
    setAccessError("");

    try {
      const [nextSettings, nextUsers] = await Promise.all([
        api.getSettings(),
        session.auth_enabled ? api.getPanelUsers() : Promise.resolve([])
      ]);
      setSettings(nextSettings);
      setUsers(nextUsers);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось загрузить настройки.";
      setSettingsError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [session.auth_enabled]);

  const currentUser = useMemo(
    () => users.find((user) => user.id === session.user_id) ?? null,
    [session.user_id, users]
  );

  const activeUsers = useMemo(() => users.filter((user) => user.is_active).length, [users]);

  async function handleSettingsSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) {
      return;
    }

    setSettingsBusy(true);
    setSettingsError("");
    setSettingsSuccess("");
    try {
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      setSettingsSuccess("Пороговые значения и интервал мониторинга сохранены.");
    } catch (err) {
      setSettingsError(err instanceof Error ? err.message : "Не удалось сохранить настройки.");
    } finally {
      setSettingsBusy(false);
    }
  }

  async function handleCreateOperator(payload: { username: string; password: string; is_active: boolean }) {
    setAccessBusy(true);
    setAccessError("");
    setAccessSuccess("");

    try {
      await api.createPanelUser(payload);
      setCreateOperatorOpen(false);
      setAccessSuccess("Новый оператор создан.");
      setUsers(await api.getPanelUsers());
    } catch (err) {
      setAccessError(err instanceof Error ? err.message : "Не удалось создать оператора.");
    } finally {
      setAccessBusy(false);
    }
  }

  async function toggleUser(user: PanelUser) {
    setAccessBusy(true);
    setAccessError("");
    setAccessSuccess("");

    try {
      await api.updatePanelUser(user.id, { is_active: !user.is_active });
      setUsers(await api.getPanelUsers());
      setAccessSuccess(user.is_active ? "Оператор отключен." : "Оператор снова активирован.");
    } catch (err) {
      setAccessError(err instanceof Error ? err.message : "Не удалось обновить оператора.");
    } finally {
      setAccessBusy(false);
    }
  }

  async function handlePasswordSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");

    if (passwordForm.newPassword.length < 8) {
      setPasswordError("Новый пароль должен быть не короче 8 символов.");
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError("Подтверждение пароля не совпадает.");
      return;
    }

    setPasswordBusy(true);
    try {
      await api.changeOwnPassword({
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword
      });
      setPasswordForm({
        currentPassword: "",
        newPassword: "",
        confirmPassword: ""
      });
      setPasswordSuccess("Пароль обновлен. Текущая сессия продолжит работать.");
      setPasswordModalOpen(false);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Не удалось изменить пароль.");
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <section className="page">
      <div className="page-hero panel">
        <div>
          <p className="eyebrow">Tuning & access</p>
          <h1>Настройки панели</h1>
        </div>
        <div className="page-hero-actions">
          <button className="secondary-button" onClick={() => setTipsOpen((current) => !current)} type="button">
            {tipsOpen ? "Скрыть советы" : "Советы"}
          </button>
        </div>
      </div>

      {settingsError ? <div className="alert error">{settingsError}</div> : null}
      {loading ? (
        <div className="panel loading-state">
          <div className="loading-spinner" aria-hidden="true" />
          <div>
            <strong>Загрузка настроек</strong>
            <p className="muted">Проверяем пороги мониторинга и доступ операторов.</p>
          </div>
        </div>
      ) : null}

      {!loading && settings ? (
        <>
          <div className="mini-metrics-grid settings-metrics-grid">
            <article className="mini-metric-card">
              <p className="summary-card-title">Scheduler</p>
              <h3>{settings.scan_interval_minutes} мин</h3>
            </article>
            <article className="mini-metric-card">
              <p className="summary-card-title">Credits risk</p>
              <h3>{settings.low_credits_threshold}</h3>
            </article>
            <article className="mini-metric-card">
              <p className="summary-card-title">Usage risk</p>
              <h3>{settings.low_usage_percent_threshold}%</h3>
            </article>
            <article className="mini-metric-card">
              <p className="summary-card-title">Операторы</p>
              <h3>{activeUsers}</h3>
            </article>
          </div>

          {tipsOpen ? (
            <section className="panel compact-help-panel">
              <ol className="steps-list">
                <li>Уменьшите интервал scheduler, если usage расходуется резко.</li>
                <li>После изменения порогов выполните ручной full scan.</li>
                <li>Не отключайте последнего активного оператора.</li>
              </ol>
            </section>
          ) : null}

          <div className="settings-layout settings-layout-single">
            <section className="panel stack settings-main-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Thresholds</p>
                  <h2>Параметры scan-движка</h2>
                </div>
              </div>

              {settingsSuccess ? <div className="alert success">{settingsSuccess}</div> : null}

              <form className="form-grid" onSubmit={handleSettingsSubmit}>
                <div className="settings-form-grid">
                  <label className="field">
                  <span>Интервал scheduler, минут</span>
                  <input
                    type="number"
                    min={15}
                    max={1440}
                    value={settings.scan_interval_minutes}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        scan_interval_minutes: Number(event.target.value)
                      })
                    }
                  />
                  </label>

                  <label className="field">
                  <span>Порог риска по credits</span>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={settings.low_credits_threshold}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        low_credits_threshold: Number(event.target.value)
                      })
                    }
                  />
                  </label>

                  <label className="field">
                  <span>Порог риска по остатку included usage, %</span>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step="0.01"
                    value={settings.low_usage_percent_threshold}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        low_usage_percent_threshold: Number(event.target.value)
                      })
                    }
                  />
                  </label>
                </div>

                <div className="form-actions">
                  <button className="primary-button" disabled={settingsBusy} type="submit">
                    {settingsBusy ? "Сохраняю..." : "Сохранить параметры"}
                  </button>
                </div>
              </form>
            </section>

            <section className="panel stack operator-settings-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Access control</p>
                  <h2>Операторы и доступ</h2>
                </div>
                <div className="button-row">
                  <button
                    className="secondary-button"
                    disabled={!session.auth_enabled}
                    onClick={() => {
                      setPasswordError("");
                      setPasswordSuccess("");
                      setPasswordModalOpen(true);
                    }}
                    type="button"
                  >
                    Сменить пароль
                  </button>
                  {session.auth_enabled ? (
                    <button className="primary-button" onClick={() => setCreateOperatorOpen(true)} type="button">
                      Добавить оператора
                    </button>
                  ) : null}
                </div>
              </div>

              {accessError ? <div className="alert error">{accessError}</div> : null}
              {accessSuccess ? <div className="alert success">{accessSuccess}</div> : null}
              {passwordSuccess ? <div className="alert success">{passwordSuccess}</div> : null}

              {!session.auth_enabled ? (
                <div className="note-card">
                  <p className="muted">
                    Авторизация панели сейчас выключена. Включите <code>AUTH_ENABLED=true</code> и перезапустите backend,
                    если хотите использовать операторов из базы.
                  </p>
                </div>
              ) : (
                <>
                  <div className="operator-profile-card">
                    <div>
                      <p className="eyebrow">Current operator</p>
                      <h3>{currentUser?.username ?? session.username ?? "не определен"}</h3>
                    </div>
                    <div className="operator-profile-meta">
                      <span className="chip chip-muted">Текущая сессия</span>
                      <span className="muted">
                        Последний вход:{" "}
                        {currentUser?.last_login_at ? new Date(currentUser.last_login_at).toLocaleString("ru-RU") : "еще не входил"}
                      </span>
                    </div>
                  </div>

                  <div className="user-list operator-user-list">
                    {users.map((user) => {
                      const isCurrent = user.id === session.user_id;
                      return (
                        <article className="user-card" key={user.id}>
                          <div className="user-card-header">
                            <div>
                              <div className="user-title-row">
                                <strong>{user.username}</strong>
                                {isCurrent ? <span className="chip chip-muted">Это вы</span> : null}
                              </div>
                              <p className="muted">
                                Последний вход:{" "}
                                {user.last_login_at ? new Date(user.last_login_at).toLocaleString("ru-RU") : "еще не входил"}
                              </p>
                            </div>
                            <span className={user.is_active ? "chip chip-success" : "chip chip-warning"}>
                              {user.is_active ? "Активен" : "Отключен"}
                            </span>
                          </div>

                          <div className="user-card-footer">
                            <span className="muted">Создан: {new Date(user.created_at).toLocaleString("ru-RU")}</span>
                            <button
                              className="secondary-button"
                              disabled={accessBusy}
                              onClick={() => void toggleUser(user)}
                              type="button"
                            >
                              {user.is_active ? "Отключить" : "Включить"}
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </>
              )}
            </section>
          </div>
        </>
      ) : null}

      <OperatorEditorModal
        busy={accessBusy}
        error={accessError}
        open={createOperatorOpen}
        onClose={() => {
          if (!accessBusy) {
            setCreateOperatorOpen(false);
          }
        }}
        onSubmit={handleCreateOperator}
      />

      <Modal
        eyebrow="Password"
        onClose={() => {
          if (!passwordBusy) {
            setPasswordModalOpen(false);
          }
        }}
        open={passwordModalOpen}
        title="Сменить пароль оператора"
      >
        <div className="note-card">
          <p className="muted">
            Текущий оператор: <strong>{currentUser?.username ?? session.username ?? "не определен"}</strong>
          </p>
        </div>

        {passwordError ? <div className="alert error">{passwordError}</div> : null}

        <form className="form-grid" onSubmit={handlePasswordSubmit}>
          <label className="field">
            <span>Текущий пароль</span>
            <input
              autoComplete="current-password"
              type="password"
              value={passwordForm.currentPassword}
              onChange={(event) => setPasswordForm({ ...passwordForm, currentPassword: event.target.value })}
              required
            />
          </label>

          <label className="field">
            <span>Новый пароль</span>
            <input
              autoComplete="new-password"
              minLength={8}
              type="password"
              value={passwordForm.newPassword}
              onChange={(event) => setPasswordForm({ ...passwordForm, newPassword: event.target.value })}
              required
            />
          </label>

          <label className="field">
            <span>Подтверждение нового пароля</span>
            <input
              autoComplete="new-password"
              minLength={8}
              type="password"
              value={passwordForm.confirmPassword}
              onChange={(event) => setPasswordForm({ ...passwordForm, confirmPassword: event.target.value })}
              required
            />
          </label>

          <div className="button-row">
            <button
              className="ghost-button"
              disabled={passwordBusy}
              onClick={() => setPasswordModalOpen(false)}
              type="button"
            >
              Отмена
            </button>
            <button className="primary-button" disabled={passwordBusy || !session.auth_enabled} type="submit">
              {passwordBusy ? "Обновляю..." : "Обновить пароль"}
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
