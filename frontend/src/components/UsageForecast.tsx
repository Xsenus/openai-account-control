import React, { useEffect, useMemo, useState } from "react";

import type { RuntimeSettings, WorkspaceSnapshot } from "../types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  snapshots: WorkspaceSnapshot[];
  settings: RuntimeSettings | null;
  emptyMessage?: string;
};

type ForecastTone = "ok" | "warning" | "danger" | "muted";

type Forecast = {
  headline: string;
  detail: string;
  tone: ForecastTone;
  remainingPercent: string;
  usageSummary: string;
  refreshSummary: string;
  creditsSummary: string;
};

const DEFAULT_SETTINGS: RuntimeSettings = {
  scan_interval_minutes: 180,
  low_credits_threshold: 15,
  low_usage_percent_threshold: 20
};

function parseNumeric(value: string | null): number | null {
  if (value === null || value === "") {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value: number | null, suffix = ""): string {
  if (value === null) {
    return "не определено";
  }

  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value)}${suffix}`;
}

function extractRefreshDate(value: string): Date | null {
  const resetAtMatch = value.match(/reset_at=([^\s|]+)/i);
  if (resetAtMatch) {
    const parsed = Date.parse(resetAtMatch[1]);
    if (!Number.isNaN(parsed)) {
      return new Date(parsed);
    }
  }

  const englishMatch = value.match(
    /\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?(?:\s+at\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:UTC|GMT)?)?/i
  );
  if (englishMatch) {
    const normalized = englishMatch[0].replace(/\sat\s/i, " ");
    const parsed = Date.parse(normalized);
    if (!Number.isNaN(parsed)) {
      return new Date(parsed);
    }
  }

  const dotDateMatch = value.match(/\b(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
  if (dotDateMatch) {
    const [, day, month, year, hours = "0", minutes = "0"] = dotDateMatch;
    return new Date(Number(year), Number(month) - 1, Number(day), Number(hours), Number(minutes));
  }

  return null;
}

function extractRefreshHours(refreshText: string | null, now: Date): number | null {
  if (!refreshText) {
    return null;
  }

  const lowered = refreshText.toLowerCase();

  const hourPatterns = [
    /in\s+(\d+(?:[.,]\d+)?)\s*(?:hour|hours|hr|hrs)/i,
    /через\s+(\d+(?:[.,]\d+)?)\s*(?:час|часа|часов)/i
  ];

  for (const pattern of hourPatterns) {
    const match = refreshText.match(pattern);
    if (match) {
      return Number(match[1].replace(",", "."));
    }
  }

  const minutePatterns = [
    /in\s+(\d+(?:[.,]\d+)?)\s*(?:minute|minutes|min|mins)/i,
    /через\s+(\d+(?:[.,]\d+)?)\s*(?:минуту|минуты|минут|мин)/i
  ];

  for (const pattern of minutePatterns) {
    const match = refreshText.match(pattern);
    if (match) {
      return Number(match[1].replace(",", ".")) / 60;
    }
  }

  const dayPatterns = [
    /in\s+(\d+(?:[.,]\d+)?)\s*(?:day|days)/i,
    /через\s+(\d+(?:[.,]\d+)?)\s*(?:день|дня|дней)/i
  ];

  for (const pattern of dayPatterns) {
    const match = refreshText.match(pattern);
    if (match) {
      return Number(match[1].replace(",", ".")) * 24;
    }
  }

  if (lowered.includes("tomorrow") || lowered.includes("завтра")) {
    return 24;
  }

  if (lowered.includes("today") || lowered.includes("сегодня")) {
    return 12;
  }

  const absoluteDate = extractRefreshDate(refreshText);
  if (!absoluteDate) {
    return null;
  }

  return (absoluteDate.getTime() - now.getTime()) / (1000 * 60 * 60);
}

function formatCountdown(hours: number | null): string {
  if (hours === null) {
    return "не определено";
  }

  if (hours <= 0) {
    return "обновление ожидается сейчас";
  }

  if (hours < 1) {
    return `через ${Math.max(1, Math.round(hours * 60))} мин`;
  }

  if (hours < 48) {
    return `через ${Math.round(hours)} ч`;
  }

  return `через ${Math.round(hours / 24)} дн`;
}

function formatResetAt(value: string | null): string | null {
  if (!value) {
    return null;
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

function formatUsageSummary(snapshot: WorkspaceSnapshot): string {
  const remaining = parseNumeric(snapshot.included_usage_remaining);
  const used = parseNumeric(snapshot.included_usage_used);
  const total = parseNumeric(snapshot.included_usage_total);

  if (remaining === null && used === null && total === null) {
    return "Структура квоты не определена";
  }

  return `Осталось ${formatNumber(remaining)} · Использовано ${formatNumber(used)} · Всего ${formatNumber(total)}`;
}

function worstCodexPercent(snapshot: WorkspaceSnapshot): number | null {
  const values = ["primary", "daily", "weekly"]
    .map((period) => parseNumeric(snapshot.codex_usage[period]?.percent_remaining ?? null))
    .filter((value): value is number => value !== null);

  return values.length > 0 ? Math.min(...values) : null;
}

function buildForecast(snapshot: WorkspaceSnapshot, settings: RuntimeSettings, now: Date): Forecast {
  const remainingPercent = worstCodexPercent(snapshot) ?? parseNumeric(snapshot.included_usage_percent_remaining);
  const credits = parseNumeric(snapshot.credits_balance);
  const dailyRefresh = snapshot.codex_usage.primary?.refresh_text ?? snapshot.codex_usage.daily?.refresh_text ?? null;
  const weeklyRefresh = snapshot.codex_usage.weekly?.refresh_text ?? null;
  const resetAtText =
    snapshot.codex_usage.primary?.reset_at ??
    snapshot.codex_usage.daily?.reset_at ??
    snapshot.codex_usage.weekly?.reset_at ??
    null;
  const refreshText = resetAtText ? `reset_at=${resetAtText}` : dailyRefresh ?? weeklyRefresh ?? snapshot.included_usage_refresh_text;
  const refreshHours = extractRefreshHours(refreshText, now);
  const refreshCountdown = formatCountdown(refreshHours);
  const formattedReset = formatResetAt(resetAtText);
  const refreshSummary = formattedReset
    ? `${refreshCountdown} · ${formattedReset}`
    : refreshText
      ? `${refreshCountdown} · ${refreshText}`
      : "Следующее обновление не определено";

  const creditsSummary =
    credits === null
      ? "Credits не определены"
      : `Credits ${formatNumber(credits)} · порог риска ${formatNumber(settings.low_credits_threshold)}`;

  if (snapshot.overall_status === "blocked" || snapshot.workspace_state === "auth_expired") {
    return {
      headline: "Есть блокер",
      detail: "Сессия недоступна или лимит уже уперся в блокирующее состояние.",
      tone: "danger",
      remainingPercent: remainingPercent === null ? "Остаток не определен" : `Осталось ${formatNumber(remainingPercent, "%")}`,
      usageSummary: formatUsageSummary(snapshot),
      refreshSummary,
      creditsSummary
    };
  }

  if (snapshot.overall_status === "deactivated") {
    return {
      headline: "Workspace отключен",
      detail: "Для этой записи сейчас нет рабочего прогноза, потому что workspace деактивирован.",
      tone: "muted",
      remainingPercent: remainingPercent === null ? "Остаток не определен" : `Осталось ${formatNumber(remainingPercent, "%")}`,
      usageSummary: formatUsageSummary(snapshot),
      refreshSummary,
      creditsSummary
    };
  }

  if (snapshot.overall_status === "partial") {
    return {
      headline: "Частичная видимость",
      detail: "Панель видит лимиты не полностью, поэтому прогноз ограничен текущими UI-данными.",
      tone: "warning",
      remainingPercent: remainingPercent === null ? "Остаток не определен" : `Осталось ${formatNumber(remainingPercent, "%")}`,
      usageSummary: formatUsageSummary(snapshot),
      refreshSummary,
      creditsSummary
    };
  }

  const isUsageLow =
    remainingPercent !== null && remainingPercent <= (settings.low_usage_percent_threshold ?? DEFAULT_SETTINGS.low_usage_percent_threshold);
  const isCreditsLow =
    credits !== null && credits <= (settings.low_credits_threshold ?? DEFAULT_SETTINGS.low_credits_threshold);

  if (snapshot.overall_status === "low" || isUsageLow || isCreditsLow) {
    return {
      headline: "Низкий остаток до обновления",
      detail:
        refreshHours === null
          ? "Остаток уже в зоне риска. Дата следующего refresh/reset не определена."
          : `Остаток уже в зоне риска и должен дотянуть до следующего обновления примерно ${refreshCountdown}.`,
      tone: "warning",
      remainingPercent: remainingPercent === null ? "Остаток не определен" : `Осталось ${formatNumber(remainingPercent, "%")}`,
      usageSummary: formatUsageSummary(snapshot),
      refreshSummary,
      creditsSummary
    };
  }

  if (remainingPercent === null && credits === null && snapshot.included_usage_refresh_text === null) {
    return {
      headline: "Недостаточно данных",
      detail: "ChatGPT UI не отдал явную картину по лимитам, поэтому точный прогноз пока невозможен.",
      tone: "muted",
      remainingPercent: "Остаток не определен",
      usageSummary: formatUsageSummary(snapshot),
      refreshSummary,
      creditsSummary
    };
  }

  return {
    headline: refreshHours === null ? "Запас есть" : "Стабильно до обновления",
    detail:
      refreshHours === null
        ? "Сейчас лимиты не выглядят критичными, но срок ближайшего обновления не распознан."
        : `Критического риска не видно. Следующее обновление ожидается ${refreshCountdown}.`,
    tone: "ok",
    remainingPercent: remainingPercent === null ? "Остаток не определен" : `Осталось ${formatNumber(remainingPercent, "%")}`,
    usageSummary: formatUsageSummary(snapshot),
    refreshSummary,
    creditsSummary
  };
}

export function UsageForecast({ snapshots, settings, emptyMessage = "Еще нет данных для прогноза." }: Props) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const effectiveSettings = settings ?? DEFAULT_SETTINGS;
  const forecasts = useMemo(
    () => snapshots.map((snapshot) => ({ snapshot, forecast: buildForecast(snapshot, effectiveSettings, now) })),
    [effectiveSettings, now, snapshots]
  );

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
          <p className="eyebrow">Forecast</p>
          <h3>Прогноз исчерпания и следующего обновления</h3>
          <p className="muted">
            Прогноз основан на текущем остатке, credits и строке refresh/reset из UI ChatGPT. Скорость расхода панель не
            угадывает.
          </p>
        </div>
      </div>

      <div className="forecast-grid">
        {forecasts.map(({ snapshot, forecast }) => (
          <article className={`forecast-card forecast-card-${forecast.tone}`} key={snapshot.id}>
            <div className="forecast-card-header">
              <div className="stack forecast-copy">
                <div className="table-primary">{snapshot.workspace_name}</div>
                <div className="muted">
                  {(snapshot.personal_plan ?? snapshot.seat_type ?? snapshot.workspace_kind) || "workspace"} ·{" "}
                  {snapshot.codex_limit_unit ?? "unknown"}
                </div>
              </div>
              <StatusBadge value={snapshot.overall_status} />
            </div>

            <div className="forecast-headline">{forecast.headline}</div>
            <p className="muted">{forecast.detail}</p>

            <div className="forecast-chip-row">
              <span className="chip chip-muted">{forecast.remainingPercent}</span>
              <span className="chip chip-muted">{forecast.refreshSummary}</span>
            </div>

            <div className="forecast-metrics">
              <div className="forecast-metric">
                <span className="metric-label">Структура квоты</span>
                <strong>{forecast.usageSummary}</strong>
              </div>
              <div className="forecast-metric">
                <span className="metric-label">Credits</span>
                <strong>{forecast.creditsSummary}</strong>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
