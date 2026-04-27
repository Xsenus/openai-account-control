import React from "react";

type Props = {
  value: string;
};

const LABELS: Record<string, string> = {
  ok: "Норма",
  low: "Низкий остаток",
  blocked: "Блокер",
  deactivated: "Отключен",
  partial: "Частично",
  unknown: "Неизвестно",
  active: "Активен",
  auth_expired: "Нужен вход",
  queued: "В очереди",
  running: "В работе",
  success: "Успешно",
  failed: "Ошибка"
};

export function StatusBadge({ value }: Props) {
  const normalizedValue = value.replace("partial_success", "partial");
  return <span className={`badge badge-${normalizedValue}`}>{LABELS[normalizedValue] ?? normalizedValue}</span>;
}
