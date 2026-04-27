import React, { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import type { ScanRun } from "../types";

type HistoryMetric = {
  label: string;
  value: number | string;
  note?: string;
};

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}

function formatDuration(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt || !finishedAt) {
    return "—";
  }
  const started = new Date(startedAt).getTime();
  const finished = new Date(finishedAt).getTime();
  if (Number.isNaN(started) || Number.isNaN(finished) || finished < started) {
    return "—";
  }
  const seconds = Math.round((finished - started) / 1000);
  if (seconds < 60) {
    return `${seconds} сек`;
  }
  return `${Math.floor(seconds / 60)} мин ${seconds % 60} сек`;
}

function metricValue(metrics: Record<string, unknown>, key: string): number | null {
  const value = metrics[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function metricsSummary(run: ScanRun): string {
  const accounts = metricValue(run.metrics, "scanned_accounts");
  const workspaces = metricValue(run.metrics, "scanned_workspaces");
  const failures = Array.isArray(run.metrics.failures) ? run.metrics.failures.length : 0;

  if (accounts === null && workspaces === null && failures === 0) {
    return "Без метрик";
  }

  return [
    accounts !== null ? `Аккаунтов: ${accounts}` : null,
    workspaces !== null ? `Workspace: ${workspaces}` : null,
    `Ошибок: ${failures}`
  ]
    .filter(Boolean)
    .join(" · ");
}

export function HistoryPage() {
  const [runs, setRuns] = useState<ScanRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setRuns(await api.getScanRuns());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить историю scan.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const metrics = useMemo<HistoryMetric[]>(() => {
    const successCount = runs.filter((run) => run.status === "success").length;
    const activeCount = runs.filter((run) => run.status === "queued" || run.status === "running").length;
    const failedCount = runs.filter((run) => run.status === "failed").length;
    const schedulerCount = runs.filter((run) => !run.manual).length;
    const lastRun = runs[0] ?? null;
    const successRate = runs.length > 0 ? Math.round((successCount / runs.length) * 100) : 0;

    return [
      { label: "Всего запусков", value: runs.length },
      { label: "Успешных", value: successCount, note: `${successRate}% success rate` },
      { label: "В процессе", value: activeCount },
      { label: "С ошибкой", value: failedCount },
      { label: "Scheduler", value: schedulerCount },
      { label: "Последний запуск", value: lastRun ? formatDate(lastRun.created_at) : "—" }
    ];
  }, [runs]);

  return (
    <section className="page">
      <div className="page-hero panel">
        <div>
          <p className="eyebrow">Execution history</p>
          <h1>История запусков</h1>
          <p className="hero-subtitle">
            Таблица показывает, какие scan jobs стартовали, когда завершились и с какими метриками или ошибками.
          </p>
        </div>
        <div className="page-hero-actions">
          <button className="secondary-button" onClick={() => void load()}>
            Обновить
          </button>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="mini-metrics-grid history-metrics-grid">
        {metrics.map((metric) => (
          <article className="mini-metric-card" key={metric.label}>
            <p className="summary-card-title">{metric.label}</p>
            <h3>{metric.value}</h3>
            {metric.note ? <span className="summary-card-meta">{metric.note}</span> : null}
          </article>
        ))}
      </div>

      {loading ? (
        <div className="panel loading-state">
          <div className="loading-spinner" aria-hidden="true" />
          <div>
            <strong>Загрузка истории</strong>
            <p className="muted">Получаем последние scan jobs и их метрики.</p>
          </div>
        </div>
      ) : runs.length === 0 ? (
        <div className="empty-state-large">
          <div className="empty-state-icon" aria-hidden="true">
            ↺
          </div>
          <div>
            <h3>Запусков пока нет</h3>
            <p>После первого обновления лимитов здесь появится история проверок.</p>
          </div>
          <button className="secondary-button" onClick={() => void load()} type="button">
            Проверить снова
          </button>
        </div>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Scope</th>
                <th>Status</th>
                <th>Тип</th>
                <th>Started</th>
                <th>Finished</th>
                <th>Duration</th>
                <th>Metrics</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td className="mono">{run.id}</td>
                  <td>{run.scope === "all" ? "Все аккаунты" : "Один аккаунт"}</td>
                  <td>
                    <StatusBadge value={run.status} />
                  </td>
                  <td>{run.manual ? "Ручной" : "Scheduler"}</td>
                  <td>{formatDate(run.started_at)}</td>
                  <td>{formatDate(run.finished_at)}</td>
                  <td>{formatDuration(run.started_at, run.finished_at)}</td>
                  <td>
                    <span className="history-metrics-summary">{metricsSummary(run)}</span>
                  </td>
                  <td>{run.error_message ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
