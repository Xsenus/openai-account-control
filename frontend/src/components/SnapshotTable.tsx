import React from "react";

import type { WorkspaceSnapshot } from "../types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  snapshots: WorkspaceSnapshot[];
  emptyMessage?: string;
};

function valueOrDash(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  return String(value);
}

function numberOrDash(value: string | null, suffix = ""): string {
  if (value === null || value === "") {
    return "—";
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return String(value);
  }

  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(parsed)}${suffix}`;
}

function autoTopupLabel(value: boolean | null): string {
  if (value === null) {
    return "—";
  }

  return value ? "Включен" : "Выключен";
}

function formatResetAt(value: string | null): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function codexPeriodSummary(snapshot: WorkspaceSnapshot, period: "daily" | "weekly"): string | null {
  const details = period === "daily" ? snapshot.codex_usage.primary ?? snapshot.codex_usage.daily : snapshot.codex_usage[period];
  if (!details) {
    return null;
  }

  const label = period === "daily" ? "Короткое окно" : "Неделя";
  const percent = numberOrDash(details.percent_remaining, "%");
  const reset = details.reset_at ? ` · обновится ${formatResetAt(details.reset_at)}` : "";
  return `${label}: ${percent} осталось${reset}`;
}

export function SnapshotTable({ snapshots, emptyMessage = "Снимков пока нет." }: Props) {
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
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Workspace</th>
            <th>Тип</th>
            <th>State</th>
            <th>Статус</th>
            <th>Plan / Seat</th>
            <th>Лимиты</th>
            <th>Credits / billing</th>
            <th>Auto top-up</th>
            <th>Проверен</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.map((snapshot) => (
            <tr key={snapshot.id}>
              <td>
                <div className="table-primary">{snapshot.workspace_name}</div>
                <div className="muted mono">{snapshot.account_id}</div>
              </td>
              <td>{snapshot.workspace_kind}</td>
              <td>{snapshot.workspace_state}</td>
              <td>
                <StatusBadge value={snapshot.overall_status} />
              </td>
              <td>
                {snapshot.personal_plan ?? snapshot.seat_type ?? "—"}
                {snapshot.role ? <div className="muted">{snapshot.role}</div> : null}
              </td>
              <td>
                <div>{valueOrDash(snapshot.included_limit_text)}</div>
                {snapshot.included_usage_percent_remaining ? (
                  <div className="muted">{numberOrDash(snapshot.included_usage_percent_remaining, "%")} осталось</div>
                ) : null}
                {snapshot.included_usage_remaining || snapshot.included_usage_total || snapshot.included_usage_used ? (
                  <div className="muted">
                    Осталось {numberOrDash(snapshot.included_usage_remaining)} · Использовано {numberOrDash(snapshot.included_usage_used)} ·
                    Всего {numberOrDash(snapshot.included_usage_total)}
                  </div>
                ) : null}
                {snapshot.included_usage_refresh_text ? (
                  <div className="muted">Обновление: {snapshot.included_usage_refresh_text}</div>
                ) : null}
                {codexPeriodSummary(snapshot, "daily") ? (
                  <div className="muted">{codexPeriodSummary(snapshot, "daily")}</div>
                ) : null}
                {codexPeriodSummary(snapshot, "weekly") ? (
                  <div className="muted">{codexPeriodSummary(snapshot, "weekly")}</div>
                ) : null}
                {snapshot.team_invitation ? (
                  <div className="muted">Invite: {snapshot.team_invitation.label ?? snapshot.team_invitation.status}</div>
                ) : null}
              </td>
              <td>
                <div>{numberOrDash(snapshot.credits_balance)}</div>
                {snapshot.spend_limit ? <div className="muted">Spend limit: {numberOrDash(snapshot.spend_limit)}</div> : null}
              </td>
              <td>{autoTopupLabel(snapshot.auto_topup_enabled)}</td>
              <td>{new Date(snapshot.checked_at).toLocaleString("ru-RU")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
