import React from "react";

import type { WorkspaceSnapshot } from "../types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  snapshots: WorkspaceSnapshot[];
  emptyMessage?: string;
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

function formatAutoTopup(value: boolean | null): string {
  if (value === null) {
    return "не определено";
  }

  return value ? "включен" : "выключен";
}

function clampPercent(value: string | null): number | null {
  const numeric = parseNumeric(value);
  if (numeric === null) {
    return null;
  }

  return Math.max(0, Math.min(100, numeric));
}

function planLabel(snapshot: WorkspaceSnapshot): string {
  return snapshot.personal_plan ?? snapshot.seat_type ?? "не определено";
}

function periodPercent(snapshot: WorkspaceSnapshot, period: "daily" | "weekly"): string | null {
  if (period === "daily" && snapshot.codex_usage.primary?.percent_remaining) {
    return snapshot.codex_usage.primary.percent_remaining;
  }
  const details = snapshot.codex_usage[period];
  return details?.percent_remaining ?? null;
}

export function UsageOverview({ snapshots, emptyMessage = "Еще нет данных по лимитам." }: Props) {
  if (snapshots.length === 0) {
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
    <section className="panel stack">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Quota picture</p>
          <h3>Текущая картина по лимитам и обновлениям</h3>
        </div>
      </div>

      <div className="usage-overview-grid">
        {snapshots.map((snapshot) => {
          const percentRemaining = clampPercent(snapshot.included_usage_percent_remaining);

          return (
            <article className="usage-card" key={snapshot.id}>
              <div className="usage-card-header">
                <div className="stack usage-card-copy">
                  <div>
                    <div className="table-primary">{snapshot.workspace_name}</div>
                    <div className="muted">
                      {snapshot.workspace_kind} · {planLabel(snapshot)}
                    </div>
                  </div>
                  {snapshot.role ? <div className="muted">Роль: {snapshot.role}</div> : null}
                </div>
                <StatusBadge value={snapshot.overall_status} />
              </div>

              <div className="usage-progress-block">
                <div className="usage-progress-head">
                  <span className="metric-label">Остаток included usage</span>
                  <strong>{percentRemaining === null ? "не определено" : `${percentRemaining}%`}</strong>
                </div>
                <div className="usage-progress-track" aria-hidden="true">
                  <span
                    className="usage-progress-fill"
                    style={{ width: `${percentRemaining ?? 0}%` }}
                  />
                </div>
              </div>

              <div className="usage-kv-grid">
                <div className="usage-kv">
                  <span className="metric-label">Единица</span>
                  <strong>{snapshot.codex_limit_unit ?? "не определено"}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Primary Codex</span>
                  <strong>{formatNumber(periodPercent(snapshot, "daily"), "%")}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Weekly Codex</span>
                  <strong>{formatNumber(periodPercent(snapshot, "weekly"), "%")}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Осталось</span>
                  <strong>{formatNumber(snapshot.included_usage_remaining)}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Использовано</span>
                  <strong>{formatNumber(snapshot.included_usage_used)}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Всего</span>
                  <strong>{formatNumber(snapshot.included_usage_total)}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Credits</span>
                  <strong>{formatNumber(snapshot.credits_balance)}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Spend limit</span>
                  <strong>{formatNumber(snapshot.spend_limit)}</strong>
                </div>
                <div className="usage-kv">
                  <span className="metric-label">Auto top-up</span>
                  <strong>{formatAutoTopup(snapshot.auto_topup_enabled)}</strong>
                </div>
                <div className="usage-kv usage-kv-wide">
                  <span className="metric-label">Следующее обновление / reset</span>
                  <strong>{snapshot.included_usage_refresh_text ?? "не определено"}</strong>
                </div>
              </div>

              {snapshot.included_limit_text ? (
                <div className="usage-footnote">
                  <span className="metric-label">Строка из UI</span>
                  <p>{snapshot.included_limit_text}</p>
                </div>
              ) : null}

              {snapshot.team_invitation ? (
                <div className="usage-footnote">
                  <span className="metric-label">Team invitation</span>
                  <p>{snapshot.team_invitation.label ?? snapshot.team_invitation.status}</p>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
