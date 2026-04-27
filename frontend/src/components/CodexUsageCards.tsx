import React from "react";

import type { CodexUsagePeriod, WorkspaceSnapshot } from "../types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  snapshots: WorkspaceSnapshot[];
  emptyMessage?: string;
};

const PERIOD_LABELS: Record<string, string> = {
  primary: "Короткое окно Codex",
  daily: "Дневной лимит",
  weekly: "Недельный лимит"
};

function parseNumeric(value: string | null): number | null {
  if (value === null || value === "") {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value: string | null, suffix = ""): string {
  const numeric = parseNumeric(value);
  if (numeric === null) {
    return "не определено";
  }

  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(numeric)}${suffix}`;
}

function clampPercent(value: string | null): number | null {
  const numeric = parseNumeric(value);
  if (numeric === null) {
    return null;
  }

  return Math.max(0, Math.min(100, numeric));
}

function resetDate(period: CodexUsagePeriod): Date | null {
  if (!period.reset_at) {
    return null;
  }

  const date = new Date(period.reset_at);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatResetAt(period: CodexUsagePeriod): string {
  const date = resetDate(period);
  if (!date) {
    return period.refresh_text ?? "не определено";
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatTimeLeft(period: CodexUsagePeriod): string {
  const date = resetDate(period);
  if (!date) {
    return "не определено";
  }

  const diffMs = date.getTime() - Date.now();
  if (diffMs <= 0) {
    return "обновляется сейчас";
  }

  const totalMinutes = Math.max(1, Math.round(diffMs / 60_000));
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

function fallbackPeriod(snapshot: WorkspaceSnapshot): CodexUsagePeriod | null {
  if (
    !snapshot.included_usage_percent_remaining &&
    !snapshot.included_usage_total &&
    !snapshot.included_usage_used &&
    !snapshot.included_usage_remaining &&
    !snapshot.included_usage_refresh_text
  ) {
    return null;
  }

  return {
    period: "included",
    percent_remaining: snapshot.included_usage_percent_remaining,
    total: snapshot.included_usage_total,
    used: snapshot.included_usage_used,
    remaining: snapshot.included_usage_remaining,
    refresh_text: snapshot.included_usage_refresh_text,
    reset_at: null,
    source_text: snapshot.included_limit_text,
    confidence: "legacy"
  };
}

function periodsForSnapshot(snapshot: WorkspaceSnapshot): CodexUsagePeriod[] {
  const keys = snapshot.codex_usage.primary ? ["primary", "weekly"] : ["daily", "weekly"];
  const structured = keys
    .map((period) => snapshot.codex_usage[period])
    .filter((period): period is CodexUsagePeriod => Boolean(period));

  if (structured.length > 0) {
    return structured;
  }

  const fallback = fallbackPeriod(snapshot);
  return fallback ? [fallback] : [];
}

export function CodexUsageCards({ snapshots, emptyMessage = "Еще нет данных по Codex лимитам." }: Props) {
  const rows = snapshots.flatMap((snapshot) =>
    periodsForSnapshot(snapshot).map((period) => ({
      snapshot,
      period
    }))
  );

  if (rows.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon" aria-hidden="true">
          —
        </div>
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <section className="panel stack codex-usage-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Codex limits</p>
          <h3>Остаток Codex по дневному и недельному лимиту</h3>
          <p className="muted">Карточки показывают распознанные лимиты из UI ChatGPT. Если daily/weekly не найдены, виден legacy included usage.</p>
        </div>
      </div>

      <div className="codex-period-grid">
        {rows.map(({ snapshot, period }) => {
          const percent = clampPercent(period.percent_remaining);
          const label = PERIOD_LABELS[period.period] ?? "Included usage";

          return (
            <article className="codex-period-card" key={`${snapshot.id}:${period.period}`}>
              <div className="codex-period-head">
                <div>
                  <div className="table-primary">{label}</div>
                  <div className="muted">{snapshot.workspace_name}</div>
                </div>
                <StatusBadge value={snapshot.overall_status} />
              </div>

              <div className="codex-percent-row">
                <strong>{percent === null ? "не определено" : `${formatNumber(String(percent), "%")}`}</strong>
                <span className="muted">осталось</span>
              </div>
              <div className="usage-progress-track" aria-hidden="true">
                <span className="usage-progress-fill" style={{ width: `${percent ?? 0}%` }} />
              </div>

              <div className="usage-kv-grid compact">
                <div className="usage-kv">
                  <span className="metric-label">Осталось</span>
                  <strong>{formatNumber(period.remaining)}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Использовано</span>
                  <strong>{formatNumber(period.used)}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Всего</span>
                  <strong>{formatNumber(period.total)}</strong>
                </div>
                <div className="usage-kv usage-kv-wide">
                  <span className="metric-label">Обновится</span>
                  <strong>{formatResetAt(period)}</strong>
                </div>
                <div className="usage-kv usage-kv-wide">
                  <span className="metric-label">Осталось до обновления</span>
                  <strong>{formatTimeLeft(period)}</strong>
                </div>
              </div>

              {snapshot.team_invitation ? (
                <div className="invite-signal">
                  <strong>Team invite</strong>
                  <span>{snapshot.team_invitation.label ?? "Найдено приглашение в team/workspace"}</span>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
