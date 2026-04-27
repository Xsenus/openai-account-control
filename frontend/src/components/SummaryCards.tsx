import React from "react";

import type { DashboardCounters } from "../types";

type Props = {
  counters: DashboardCounters;
};

type CardTone = "default" | "success" | "warning" | "danger";

type CardConfig = {
  title: string;
  value: string | number;
  tone?: CardTone;
};

function SummaryCard({ title, value, tone = "default" }: CardConfig) {
  const className = tone === "default" ? "summary-card" : `summary-card summary-card-${tone}`;
  return (
    <article className={className}>
      <div>
        <p className="summary-card-title">{title}</p>
        <h3>{value}</h3>
      </div>
    </article>
  );
}

export function SummaryCards({ counters }: Props) {
  const attentionCount = counters.workspaces_blocked + counters.workspaces_low + counters.workspaces_partial;
  const sessionCoverage =
    counters.total_accounts > 0 ? Math.round((counters.with_valid_session / counters.total_accounts) * 100) : 0;
  const cards: CardConfig[] = [
    {
      title: "Аккаунты",
      value: `${counters.active_accounts}/${counters.total_accounts}`
    },
    {
      title: "Покрытие сессиями",
      value: `${sessionCoverage}%`,
      tone: sessionCoverage >= 80 || counters.total_accounts === 0 ? "success" : "warning"
    },
    {
      title: "Workspace в норме",
      value: counters.workspaces_ok,
      tone: "success"
    },
    {
      title: "Требуют внимания",
      value: attentionCount,
      tone: attentionCount > 0 ? "danger" : "success"
    }
  ];

  return (
    <section className="summary-grid">
      {cards.map((card) => (
        <SummaryCard key={card.title} {...card} />
      ))}
    </section>
  );
}
