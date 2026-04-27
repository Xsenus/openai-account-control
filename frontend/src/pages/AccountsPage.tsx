import React, { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import { api } from "../api/client";
import { AccountEditorModal } from "../components/AccountEditorModal";
import { CodexUsageCards } from "../components/CodexUsageCards";
import { SnapshotTable } from "../components/SnapshotTable";
import { StorageStateHelpModal } from "../components/StorageStateHelpModal";
import { StatusBadge } from "../components/StatusBadge";
import { UsageForecast } from "../components/UsageForecast";
import { UsageOverview } from "../components/UsageOverview";
import type { Account, AccountDraft, AuthJob, RuntimeSettings, ScanRun, WorkspaceSnapshot } from "../types";

type SnapshotsByAccount = Record<string, WorkspaceSnapshot[]>;
type DirectoryFilter = "all" | "active" | "needsSession";
type EditorMode = "create" | "edit" | null;

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}

function formatAccountLimitSummary(snapshots: WorkspaceSnapshot[]): string {
  const percents = snapshots.flatMap((snapshot) =>
    ["primary", "daily", "weekly"]
      .map((period) => snapshot.codex_usage[period]?.percent_remaining ?? null)
      .filter((value): value is string => value !== null && value !== "")
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value))
  );

  if (percents.length === 0) {
    return "Codex: нет данных";
  }

  const worst = Math.min(...percents);
  return `Codex min: ${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(worst)}%`;
}

function hasTeamInvitation(snapshots: WorkspaceSnapshot[]): boolean {
  return snapshots.some((snapshot) => Boolean(snapshot.team_invitation));
}

export function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [snapshotsByAccount, setSnapshotsByAccount] = useState<SnapshotsByAccount>({});
  const [runtimeSettings, setRuntimeSettings] = useState<RuntimeSettings | null>(null);
  const [authJobs, setAuthJobs] = useState<Record<string, AuthJob>>({});
  const [selectedHistory, setSelectedHistory] = useState<WorkspaceSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busyAccountId, setBusyAccountId] = useState("");
  const [scanMessage, setScanMessage] = useState("");
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<DirectoryFilter>("all");
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [editorMode, setEditorMode] = useState<EditorMode>(null);
  const [editorBusy, setEditorBusy] = useState(false);
  const [editorError, setEditorError] = useState("");
  const [helpOpen, setHelpOpen] = useState(false);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const deferredSearch = useDeferredValue(search);

  async function load() {
    const hasExistingData = accounts.length > 0;
    if (hasExistingData) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const [fetchedAccounts, fetchedSettings, latestSnapshots] = await Promise.all([
        api.getAccounts(),
        api.getSettings().catch(() => null),
        api.getLatestAccountSnapshots()
      ]);
      setAccounts(fetchedAccounts);
      setRuntimeSettings(fetchedSettings);

      const nextSnapshots: SnapshotsByAccount = {};
      for (const snapshot of latestSnapshots) {
        nextSnapshots[snapshot.account_id] = [...(nextSnapshots[snapshot.account_id] ?? []), snapshot];
      }

      setSnapshotsByAccount(nextSnapshots);
      setSelectedAccountId((current) =>
        fetchedAccounts.some((account) => account.id === current) ? current : fetchedAccounts[0]?.id ?? ""
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить учетные записи.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function loadSelectedHistory(accountId: string) {
    if (!accountId) {
      setSelectedHistory([]);
      return;
    }

    try {
      setSelectedHistory(await api.getAccountSnapshots(accountId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить историю выбранной учетки.");
    }
  }

  const filteredAccounts = useMemo(() => {
    const query = deferredSearch.trim().toLowerCase();

    return accounts.filter((account) => {
      if (filter === "active" && !account.is_enabled) {
        return false;
      }
      if (filter === "needsSession" && account.has_session_state) {
        return false;
      }

      if (!query) {
        return true;
      }

      const haystack = [account.label, account.email_hint ?? "", account.notes]
        .join(" ")
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [accounts, deferredSearch, filter]);

  useEffect(() => {
    if (filteredAccounts.length === 0) {
      setSelectedAccountId("");
      return;
    }

    if (!filteredAccounts.some((account) => account.id === selectedAccountId)) {
      setSelectedAccountId(filteredAccounts[0].id);
    }
  }, [filteredAccounts, selectedAccountId]);

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.id === selectedAccountId) ?? null,
    [accounts, selectedAccountId]
  );

  const selectedSnapshots = selectedAccount ? snapshotsByAccount[selectedAccount.id] ?? [] : [];
  const latestSelectedSnapshots = useMemo(() => {
    const seen = new Set<string>();
    const items: WorkspaceSnapshot[] = [];

    for (const snapshot of selectedSnapshots) {
      const key = `${snapshot.account_id}:${snapshot.workspace_name}`;
      if (seen.has(key)) {
        continue;
      }

      seen.add(key);
      items.push(snapshot);
    }

    return items;
  }, [selectedSnapshots]);
  const selectedAuthJob = selectedAccount ? authJobs[selectedAccount.id] : undefined;

  useEffect(() => {
    void loadSelectedHistory(selectedAccountId);
  }, [selectedAccountId]);

  const counts = useMemo(
    () => ({
      total: accounts.length,
      active: accounts.filter((account) => account.is_enabled).length,
      withSession: accounts.filter((account) => account.has_session_state).length,
      needsSession: accounts.filter((account) => !account.has_session_state).length
    }),
    [accounts]
  );

  async function handleEditorSubmit(payload: AccountDraft) {
    setEditorBusy(true);
    setEditorError("");

    try {
      if (editorMode === "create") {
        await api.createAccount(payload);
      } else if (editorMode === "edit" && selectedAccount) {
        await api.updateAccount(selectedAccount.id, payload);
      }

      setEditorMode(null);
      await load();
    } catch (err) {
      setEditorError(err instanceof Error ? err.message : "Не удалось сохранить учетную запись.");
    } finally {
      setEditorBusy(false);
    }
  }

  async function deleteAccount(accountId: string) {
    if (!window.confirm("Удалить учетку и всю ее историю scan?")) {
      return;
    }

    setBusyAccountId(accountId);
    setError("");

    try {
      await api.deleteAccount(accountId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось удалить учетку.");
    } finally {
      setBusyAccountId("");
    }
  }

  async function runScan(accountId: string) {
    setBusyAccountId(accountId);
    setScanMessage("Запускаю обновление лимитов...");
    setError("");

    try {
      const run = await api.startAccountScan(accountId);
      const finishedRun = await waitForScanRun(run);
      if (finishedRun.status === "failed") {
        throw new Error(finishedRun.error_message ?? "Scan завершился ошибкой.");
      }
      await load();
      await loadSelectedHistory(accountId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось запустить scan.");
    } finally {
      setBusyAccountId("");
      setScanMessage("");
    }
  }

  async function waitForScanRun(initialRun: ScanRun): Promise<ScanRun> {
    let currentRun = initialRun;
    const terminalStatuses = new Set(["success", "partial_success", "failed"]);

    for (let attempt = 0; attempt < 120; attempt += 1) {
      setScanMessage(
        currentRun.status === "queued"
          ? "Scan в очереди..."
          : currentRun.status === "running"
            ? "Собираю лимиты из ChatGPT UI..."
            : "Обновляю данные..."
      );

      if (terminalStatuses.has(currentRun.status)) {
        return currentRun;
      }

      await new Promise((resolve) => window.setTimeout(resolve, 2000));
      currentRun = await api.getScanRun(currentRun.id);
    }

    throw new Error("Scan не завершился за ожидаемое время. Проверьте историю запусков.");
  }

  async function startLocalLogin(accountId: string) {
    setBusyAccountId(accountId);
    setError("");

    try {
      const job = await api.startLocalLogin(accountId, { timeout_seconds: 900, headless: false });
      setAuthJobs((prev) => ({ ...prev, [accountId]: job }));
      const finishedJob = await pollAuthJob(accountId, job.job_id);
      if (finishedJob.status === "failed") {
        throw new Error(finishedJob.message);
      }
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Не удалось запустить локальную авторизацию. Проверьте, что backend запущен на этом компьютере."
      );
    } finally {
      setBusyAccountId("");
    }
  }

  async function pollAuthJob(accountId: string, jobId: string): Promise<AuthJob> {
    let attempts = 0;
    while (attempts < 300) {
      const job = await api.getLocalLoginJob(accountId, jobId);
      setAuthJobs((prev) => ({ ...prev, [accountId]: job }));

      if (job.status === "success" || job.status === "failed") {
        return job;
      }

      attempts += 1;
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }

    throw new Error("Локальный вход не завершился за ожидаемое время.");
  }

  async function importStateFromFile(accountId: string, file: File) {
    setBusyAccountId(accountId);
    setError("");

    try {
      const text = await file.text();
      let json: unknown;
      try {
        json = JSON.parse(text);
      } catch {
        throw new Error("Файл не похож на JSON. Нужен Playwright storage_state с полями cookies и origins.");
      }
      await api.importSessionState(accountId, json);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось импортировать storage_state JSON.");
    } finally {
      setBusyAccountId("");
    }
  }

  function openCreateModal() {
    setEditorError("");
    setEditorMode("create");
  }

  function openEditModal() {
    if (!selectedAccount) {
      return;
    }

    setEditorError("");
    setEditorMode("edit");
  }

  function openImportDialog() {
    fileInputRef.current?.click();
  }

  const selectedBusy = selectedAccount ? busyAccountId === selectedAccount.id : false;

  return (
    <section className="page">
      <div className="page-hero panel hero-accent">
        <div>
          <p className="eyebrow">Accounts registry</p>
          <h1>Управление учетными записями</h1>
          <p className="hero-subtitle">
            Список учеток, их статус и ручные действия разделены на отдельные уровни интерфейса: слева реестр, справа
            контекст выбранной записи.
          </p>
        </div>

        <div className="page-hero-actions">
          <button className="secondary-button" onClick={() => void load()}>
            {refreshing ? "Обновляю..." : "Обновить данные"}
          </button>
          <button className="primary-button" onClick={openCreateModal}>
            Добавить учетку
          </button>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="mini-metrics-grid">
        <article className="mini-metric-card">
          <p className="summary-card-title">Всего учеток</p>
          <h3>{counts.total}</h3>
        </article>
        <article className="mini-metric-card">
          <p className="summary-card-title">Активных</p>
          <h3>{counts.active}</h3>
        </article>
        <article className="mini-metric-card">
          <p className="summary-card-title">С живой сессией</p>
          <h3>{counts.withSession}</h3>
        </article>
        <article className="mini-metric-card">
          <p className="summary-card-title">Без сессии</p>
          <h3>{counts.needsSession}</h3>
        </article>
      </div>

      <div className="accounts-workspace">
        <aside className="panel account-directory">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Directory</p>
              <h2>Реестр учеток</h2>
            </div>
            <div className="directory-count">{filteredAccounts.length}</div>
          </div>

          <label className="field">
            <span>Поиск</span>
            <input
              className="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Название, email hint или заметки"
            />
          </label>

          <div className="segmented-control">
            <button
              className={filter === "all" ? "segmented-button active" : "segmented-button"}
              onClick={() => setFilter("all")}
              type="button"
            >
              Все
            </button>
            <button
              className={filter === "active" ? "segmented-button active" : "segmented-button"}
              onClick={() => setFilter("active")}
              type="button"
            >
              Активные
            </button>
            <button
              className={filter === "needsSession" ? "segmented-button active" : "segmented-button"}
              onClick={() => setFilter("needsSession")}
              type="button"
            >
              Без сессии
            </button>
          </div>

          {loading && accounts.length === 0 ? (
            <div className="loading-state">
              <div className="loading-spinner" aria-hidden="true" />
              <div>
                <strong>Загрузка учеток</strong>
                <p className="muted">Собираем реестр и последние снимки.</p>
              </div>
            </div>
          ) : filteredAccounts.length === 0 ? (
            <div className="empty-state-large">
              <div className="empty-state-icon" aria-hidden="true">
                —
              </div>
              <p>Под фильтр ничего не попало.</p>
              <button className="ghost-button" onClick={openCreateModal} type="button">
                Создать первую учетку
              </button>
            </div>
          ) : (
            <div className="account-list">
              {filteredAccounts.map((account) => (
                <button
                  className={account.id === selectedAccount?.id ? "account-list-item selected" : "account-list-item"}
                  key={account.id}
                  onClick={() => setSelectedAccountId(account.id)}
                  type="button"
                >
                  <div className="account-list-top">
                    <div>
                      <strong>{account.label}</strong>
                      <div className="muted">{account.email_hint ?? "Без email hint"}</div>
                    </div>
                    <span className={account.is_enabled ? "chip chip-success" : "chip chip-muted"}>
                      {account.is_enabled ? "Активна" : "Выключена"}
                    </span>
                  </div>

                  <div className="account-list-bottom">
                    <span className={account.has_session_state ? "chip chip-success" : "chip chip-warning"}>
                      {account.has_session_state ? "Сессия есть" : "Нужна сессия"}
                    </span>
                    <span className="muted">{formatAccountLimitSummary(snapshotsByAccount[account.id] ?? [])}</span>
                    {hasTeamInvitation(snapshotsByAccount[account.id] ?? []) ? (
                      <span className="chip chip-warning">Team invite</span>
                    ) : null}
                    <span className="muted">Scan: {formatDate(account.last_scan_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </aside>

        <div className="account-detail-stack">
          {selectedAccount ? (
            <>
              <article className="panel account-detail-hero">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Selected account</p>
                    <h2>{selectedAccount.label}</h2>
                    <p className="muted">{selectedAccount.email_hint ?? "Email hint не указан"}</p>
                  </div>

                  <div className="button-row button-row-wrap">
                    <button className="secondary-button" disabled={selectedBusy} onClick={openEditModal} type="button">
                      Редактировать
                    </button>
                    <button
                      className="primary-button"
                      disabled={selectedBusy}
                      onClick={() => void runScan(selectedAccount.id)}
                      type="button"
                    >
                      Обновить лимиты
                    </button>
                    <button
                      className="secondary-button"
                      disabled={selectedBusy}
                      onClick={() => void startLocalLogin(selectedAccount.id)}
                      type="button"
                    >
                      Локальный вход
                    </button>
                    <button
                      className="secondary-button"
                      disabled={selectedBusy}
                      onClick={openImportDialog}
                      type="button"
                    >
                      Импорт JSON
                    </button>
                    <button className="ghost-button" onClick={() => setHelpOpen(true)} type="button">
                      Как получить JSON
                    </button>
                    <button className="ghost-button" onClick={() => setOnboardingOpen((current) => !current)} type="button">
                      {onboardingOpen ? "Скрыть памятку" : "Памятка"}
                    </button>
                    <button
                      className="danger-button"
                      disabled={selectedBusy}
                      onClick={() => void deleteAccount(selectedAccount.id)}
                      type="button"
                    >
                      Удалить
                    </button>
                  </div>
                </div>

                <div className="chip-row">
                  <span className={selectedAccount.has_session_state ? "chip chip-success" : "chip chip-warning"}>
                    {selectedAccount.has_session_state ? "Playwright session сохранена" : "Сессия еще не сохранена"}
                  </span>
                  <span className={selectedAccount.is_enabled ? "chip chip-success" : "chip chip-muted"}>
                    {selectedAccount.is_enabled ? "Участвует в scheduler" : "Исключена из scheduler"}
                  </span>
                  <span className="chip chip-muted">Auth method: {selectedAccount.auth_method}</span>
                </div>

                <div className="metric-grid">
                  <article className="metric-card">
                    <span className="metric-label">Последний auth</span>
                    <strong className="metric-value">{formatDate(selectedAccount.last_auth_at)}</strong>
                  </article>
                  <article className="metric-card">
                    <span className="metric-label">Последний scan</span>
                    <strong className="metric-value">{formatDate(selectedAccount.last_scan_at)}</strong>
                  </article>
                  <article className="metric-card">
                    <span className="metric-label">Создана</span>
                    <strong className="metric-value">{formatDate(selectedAccount.created_at)}</strong>
                  </article>
                  <article className="metric-card">
                    <span className="metric-label">ID</span>
                    <strong className="metric-value mono">{selectedAccount.id}</strong>
                  </article>
                </div>
              </article>

              {onboardingOpen ? (
                <section className="panel stack compact-help-panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">Onboarding</p>
                      <h3>Как подготовить учетку к мониторингу</h3>
                    </div>
                  </div>

                  <ol className="steps-list">
                    <li>Сначала заполните карточку учетки через модальное окно создания или редактирования.</li>
                    <li>Сохраните Playwright session-state локальным входом или через импорт JSON-файла.</li>
                    <li>После сохранения сессии запустите ручной scan и проверьте, что workspace-статусы читаются корректно.</li>
                    <li>Если учетку не надо включать в фоновые проверки, выключите флаг участия в scheduler.</li>
                  </ol>

                  <div className="info-card-grid">
                    <article className="note-card">
                      <strong>Локальный вход</strong>
                      <p className="muted">
                        Используйте его только когда backend запущен на этом же ПК и может открыть видимое окно
                        Chromium.
                      </p>
                    </article>

                    <article className="note-card">
                      <strong>Импорт JSON</strong>
                      <p className="muted">
                        Нужен именно Playwright <code>storage_state</code> с верхними полями <code>cookies</code> и{" "}
                        <code>origins</code>.
                      </p>
                    </article>
                  </div>
                </section>
              ) : null}

              {selectedAuthJob ? (
                <div className="alert info">
                  <div className="inline-status">
                    <strong>Статус локального входа</strong>
                    <StatusBadge value={selectedAuthJob.status} />
                  </div>
                  <p>{selectedAuthJob.message}</p>
                </div>
              ) : null}

              {scanMessage && selectedBusy ? (
                <div className="alert info">
                  <strong>Обновление лимитов</strong>
                  <p>{scanMessage}</p>
                </div>
              ) : null}

              <CodexUsageCards
                snapshots={latestSelectedSnapshots}
                emptyMessage="После первого успешного scan здесь появятся дневной и недельный лимиты Codex."
              />

              <UsageForecast
                snapshots={latestSelectedSnapshots}
                settings={runtimeSettings}
                emptyMessage="После первого успешного scan здесь появится прогноз по остатку и следующему обновлению лимитов."
              />

              <UsageOverview
                snapshots={latestSelectedSnapshots}
                emptyMessage="После первого успешного scan здесь появится сводка по остаткам, total и следующему обновлению лимитов."
              />

              <section className="stack">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Workspace history</p>
                    <h3>Последние snapshots выбранной учетки</h3>
                  </div>
                </div>
                <SnapshotTable
                  snapshots={selectedHistory.slice(0, 20)}
                  emptyMessage="У этой учетки пока нет snapshots. После сохранения сессии запустите первый scan."
                />
              </section>
            </>
          ) : (
            <div className="empty-state-large">
              <div className="empty-state-icon" aria-hidden="true">
                —
              </div>
              <p>Выберите учетку слева или создайте новую.</p>
              <button className="primary-button" onClick={openCreateModal} type="button">
                Добавить учетку
              </button>
            </div>
          )}
        </div>
      </div>

      <AccountEditorModal
        account={editorMode === "edit" ? selectedAccount : null}
        busy={editorBusy}
        error={editorError}
        mode={editorMode}
        onClose={() => {
          if (!editorBusy) {
            setEditorMode(null);
          }
        }}
        onSubmit={handleEditorSubmit}
      />

      <StorageStateHelpModal
        accountId={selectedAccount?.id ?? ""}
        open={helpOpen}
        onClose={() => setHelpOpen(false)}
      />

      <input
        accept=".json,application/json"
        hidden
        ref={fileInputRef}
        type="file"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file && selectedAccount) {
            void importStateFromFile(selectedAccount.id, file);
          }
          event.currentTarget.value = "";
        }}
      />
    </section>
  );
}
