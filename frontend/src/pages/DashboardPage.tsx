import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { SnapshotTable } from "../components/SnapshotTable";
import { SummaryCards } from "../components/SummaryCards";
import type { CodexUsagePeriod, DashboardSummary, WorkspaceSnapshot } from "../types";

type Signal = {
  label: string;
  value: number;
  tone: "ok" | "warning" | "danger";
};

type LimitCardData = {
  label: string;
  percent: number | null;
  remaining: string;
  reset: string;
  resetHint: string;
};

function numericPercent(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, Math.min(100, parsed)) : null;
}

function formatNumber(value: string | null | undefined): string {
  if (!value) {
    return "нет данных";
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(parsed) : value;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "не определено";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function formatTimeLeft(value: string | null | undefined): string {
  if (!value) {
    return "время неизвестно";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "время неизвестно";
  }
  const diffMs = date.getTime() - Date.now();
  if (diffMs <= 0) {
    return "обновление ожидается";
  }
  const totalMinutes = Math.ceil(diffMs / 60_000);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) {
    return `${days} д ${hours} ч`;
  }
  if (hours > 0) {
    return `${hours} ч ${minutes} мин`;
  }
  return `${minutes} мин`;
}

function buildLimitCard(label: string, period: CodexUsagePeriod | undefined): LimitCardData {
  const percent = numericPercent(period?.percent_remaining);
  const remaining = period
    ? `${formatNumber(period.remaining)} осталось${period.total ? ` из ${formatNumber(period.total)}` : ""}`
    : "нет данных по лимиту";
  return {
    label,
    percent,
    remaining,
    reset: formatDateTime(period?.reset_at),
    resetHint: formatTimeLeft(period?.reset_at)
  };
}

function pickFocusSnapshot(snapshots: WorkspaceSnapshot[]): WorkspaceSnapshot | null {
  return (
    snapshots.find((snapshot) => snapshot.codex_usage.primary || snapshot.codex_usage.daily || snapshot.codex_usage.weekly) ??
    snapshots[0] ??
    null
  );
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState("");
  const [stateOpen, setStateOpen] = useState(false);
  const [attentionOpen, setAttentionOpen] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api.getDashboardSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить дашборд.");
    } finally {
      setLoading(false);
    }
  }

  async function triggerScan() {
    setScanning(true);
    setScanMessage("Запускаю обновление лимитов всех учеток...");
    setError("");
    try {
      let run = await api.startInventoryScan();
      const terminalStatuses = new Set(["success", "partial_success", "failed"]);
      for (let attempt = 0; attempt < 120 && !terminalStatuses.has(run.status); attempt += 1) {
        setScanMessage(run.status === "queued" ? "Scan в очереди..." : "Собираю данные из ChatGPT UI...");
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        run = await api.getScanRun(run.id);
      }
      if (!terminalStatuses.has(run.status)) {
        throw new Error("Scan не завершился за ожидаемое время. Проверьте историю запусков.");
      }
      if (run.status === "failed") {
        throw new Error(run.error_message ?? "Полная проверка завершилась ошибкой.");
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось запустить полную проверку.");
    } finally {
      setScanning(false);
      setScanMessage("");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const signals = useMemo<Signal[]>(() => {
    if (!data) {
      return [];
    }

    return [
      {
        label: "Блокеры",
        value: data.counters.workspaces_blocked,
        tone: "danger"
      },
      {
        label: "Низкий остаток",
        value: data.counters.workspaces_low,
        tone: "warning"
      },
      {
        label: "Частичная видимость",
        value: data.counters.workspaces_partial,
        tone: "warning"
      },
      {
        label: "Готовы к работе",
        value: data.counters.with_valid_session,
        tone: "ok"
      }
    ];
  }, [data]);

  const dashboardState = useMemo(() => {
    if (!data) {
      return null;
    }

    const attentionCount =
      data.counters.workspaces_blocked + data.counters.workspaces_low + data.counters.workspaces_partial;
    const activeRuns = data.latest_runs.filter((run) => run.status === "queued" || run.status === "running").length;
    const sessionCoverage =
      data.counters.total_accounts > 0
        ? Math.round((data.counters.with_valid_session / data.counters.total_accounts) * 100)
        : 0;

    if (data.counters.total_accounts === 0) {
      return {
        tone: "warning",
        title: "Нужно добавить первую учетку",
        attentionCount,
        activeRuns,
        sessionCoverage
      };
    }

    if (attentionCount > 0) {
      return {
        tone: "danger",
        title: "Есть зоны внимания",
        attentionCount,
        activeRuns,
        sessionCoverage
      };
    }

    return {
      tone: "ok",
      title: activeRuns > 0 ? "Scan сейчас выполняется" : "Система выглядит стабильно",
      attentionCount,
      activeRuns,
      sessionCoverage
    };
  }, [data]);

  const focusSnapshot = useMemo(() => (data ? pickFocusSnapshot(data.latest_snapshots) : null), [data]);
  const accountWorkspaces = useMemo(() => {
    if (!data || !focusSnapshot) {
      return [];
    }
    return data.latest_snapshots.filter((snapshot) => snapshot.account_id === focusSnapshot.account_id);
  }, [data, focusSnapshot]);
  const dailyLimit = buildLimitCard("Дневной лимит", focusSnapshot?.codex_usage.primary ?? focusSnapshot?.codex_usage.daily);
  const weeklyLimit = buildLimitCard("Еженедельный лимит", focusSnapshot?.codex_usage.weekly);

  return (
    <section className="page">
      <div className="page-hero panel hero-accent">
        <div>
          <p className="eyebrow">Operations overview</p>
          <h1>Дашборд мониторинга</h1>
        </div>
        {dashboardState ? (
          <button
            aria-label={`Зоны внимания: ${dashboardState.attentionCount}`}
            className={attentionOpen ? "attention-dot active" : "attention-dot"}
            onClick={() => setAttentionOpen((current) => !current)}
            title={`Зоны внимания: ${dashboardState.attentionCount}`}
            type="button"
          >
            {dashboardState.attentionCount > 0 ? <span>{dashboardState.attentionCount}</span> : null}
          </button>
        ) : null}

        <div className="page-hero-actions">
          <button className="secondary-button" onClick={() => void load()}>
            Обновить данные
          </button>
          <button
            className="primary-button"
            disabled={scanning}
            onClick={() => void triggerScan()}
            title="Запустить обновление Codex-лимитов для всех учетных записей"
            type="button"
          >
            {scanning ? "Scan выполняется..." : "Обновить лимиты"}
          </button>
          <Link className="secondary-button" to="/accounts">
            Учетные записи
          </Link>
          <Link className="secondary-button" to="/history">
            История
          </Link>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}
      {scanMessage ? (
        <div className="alert info">
          <strong>Полное обновление</strong>
          <p>{scanMessage}</p>
        </div>
      ) : null}
      {loading && !data ? (
        <div className="panel loading-state">
          <div className="loading-spinner" aria-hidden="true" />
          <div>
            <strong>Загрузка дашборда</strong>
          </div>
        </div>
      ) : null}

      {data ? (
        <>
          {dashboardState ? (
            <section className="dashboard-top-grid">
              <article className="panel account-limit-card">
                <div className="account-limit-head">
                  <div>
                    <p className="eyebrow">Primary account</p>
                    <h2>{focusSnapshot?.workspace_name ?? "Аккаунт пока не выбран"}</h2>
                    <p className="muted">
                      {focusSnapshot
                        ? `Account ID: ${focusSnapshot.account_id} · ${accountWorkspaces.length} workspace`
                        : "Нет данных"}
                    </p>
                  </div>
                  {focusSnapshot ? (
                    <span className="summary-card-meta">Проверен {formatDateTime(focusSnapshot.checked_at)}</span>
                  ) : null}
                </div>

                <div className="limit-panels">
                  {[dailyLimit, weeklyLimit].map((limit) => (
                    <div className="limit-panel" key={limit.label}>
                      <div className="limit-panel-head">
                        <div>
                          <span className="metric-label">{limit.label}</span>
                          <strong>{limit.percent === null ? "Нет данных" : `${Math.round(limit.percent)}%`}</strong>
                        </div>
                        <span className="summary-card-meta">{limit.resetHint}</span>
                      </div>
                      <div className="usage-progress-track" aria-label={`${limit.label}: ${limit.percent ?? 0}% осталось`}>
                        <span className="usage-progress-fill" style={{ width: `${limit.percent ?? 0}%` }} />
                      </div>
                      <div className="limit-meta-grid">
                        <div>
                          <span className="metric-label">Осталось</span>
                          <strong>{limit.remaining}</strong>
                        </div>
                        <div>
                          <span className="metric-label">Обновление</span>
                          <strong>{limit.reset}</strong>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <aside className="dashboard-side-stack">
                <article className={`panel dashboard-status dashboard-status-${dashboardState.tone}`}>
                  <div className="dashboard-status-compact">
                    <div className="dashboard-status-head">
                      <span className="status-dot" aria-hidden="true" />
                      <div>
                        <p className="eyebrow">Current state</p>
                        <h2>{dashboardState.title}</h2>
                      </div>
                    </div>
                    <button className="secondary-button" onClick={() => setStateOpen((current) => !current)} type="button">
                      {stateOpen ? "Скрыть" : "Подробнее"}
                    </button>
                  </div>
                  {stateOpen ? (
                    <>
                      <div className="dashboard-facts">
                        <div>
                          <span className="metric-label">Требуют внимания</span>
                          <strong>{dashboardState.attentionCount}</strong>
                        </div>
                        <div>
                          <span className="metric-label">Активные scan jobs</span>
                          <strong>{dashboardState.activeRuns}</strong>
                        </div>
                        <div>
                          <span className="metric-label">Покрытие сессиями</span>
                          <strong>{dashboardState.sessionCoverage}%</strong>
                        </div>
                      </div>
                    </>
                  ) : null}
                </article>
              </aside>
            </section>
          ) : null}

          <SummaryCards counters={data.counters} />

          {dashboardState && attentionOpen ? (
            <section className="panel attention-collapsible">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Attention zone</p>
                  <h2>Куда смотреть в первую очередь</h2>
                </div>
              </div>
              <div className="signal-list attention-list">
                {signals.map((signal) => (
                  <article className={`signal-card signal-card-${signal.tone}`} key={signal.label}>
                    <div className="signal-value">{signal.value}</div>
                    <div>
                      <strong>{signal.label}</strong>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          <section className="snapshot-section">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Latest workspace state</p>
                <h2>Последние подтвержденные snapshots</h2>
              </div>
            </div>
            <SnapshotTable snapshots={data.latest_snapshots} emptyMessage="Снимков пока нет. Выполните первый scan." />
          </section>
        </>
      ) : null}
    </section>
  );
}
