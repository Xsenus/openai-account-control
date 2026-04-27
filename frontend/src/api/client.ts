import type {
  Account,
  AccountDraft,
  AuthJob,
  AuthSession,
  DashboardSummary,
  PanelUser,
  RuntimeSettings,
  ScanRun,
  WorkspaceSnapshot
} from "../types";

const API_BASE = "";

type UnauthorizedHandler = (() => void) | null;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let unauthorizedHandler: UnauthorizedHandler = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler) {
  unauthorizedHandler = handler;
}

async function extractError(response: Response): Promise<ApiError> {
  const contentType = response.headers.get("content-type") ?? "";
  let message = `HTTP ${response.status}`;

  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as { detail?: string; message?: string };
    message = payload.detail ?? payload.message ?? message;
  } else {
    const text = await response.text();
    if (text.trim()) {
      message = text;
    }
  }

  return new ApiError(message, response.status);
}

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  const hasJsonBody = init?.body !== undefined && !(init.body instanceof FormData);
  if (hasJsonBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${input}`, {
    credentials: "include",
    ...init,
    headers
  });

  if (!response.ok) {
    const error = await extractError(response);
    if (error.status === 401 && !input.startsWith("/api/auth/")) {
      unauthorizedHandler?.();
    }
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  getAuthSession: () => request<AuthSession>("/api/auth/session"),
  login: (payload: { username: string; password: string }) =>
    request<AuthSession>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  logout: () =>
    request<AuthSession>("/api/auth/logout", {
      method: "POST"
    }),
  getDashboardSummary: () => request<DashboardSummary>("/api/dashboard/summary"),
  getAccounts: () => request<Account[]>("/api/accounts"),
  createAccount: (payload: AccountDraft) =>
    request<Account>("/api/accounts", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateAccount: (accountId: string, payload: Partial<AccountDraft>) =>
    request<Account>(`/api/accounts/${accountId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteAccount: (accountId: string) =>
    request<{ message: string }>(`/api/accounts/${accountId}`, { method: "DELETE" }),
  importSessionState: (accountId: string, storageState: unknown) =>
    request<Account>(`/api/accounts/${accountId}/auth/import`, {
      method: "POST",
      body: JSON.stringify({ storage_state: storageState })
    }),
  startLocalLogin: (accountId: string, payload?: { timeout_seconds?: number; headless?: boolean }) =>
    request<AuthJob>(`/api/accounts/${accountId}/auth/browser-login`, {
      method: "POST",
      body: JSON.stringify({
        timeout_seconds: payload?.timeout_seconds ?? 600,
        headless: payload?.headless ?? false
      })
    }),
  getLocalLoginJob: (accountId: string, jobId: string) =>
    request<AuthJob>(`/api/accounts/${accountId}/auth/browser-login/${jobId}`),
  getAccountSnapshots: (accountId: string) => request<WorkspaceSnapshot[]>(`/api/accounts/${accountId}/snapshots`),
  getLatestAccountSnapshots: () => request<WorkspaceSnapshot[]>("/api/accounts/snapshots/latest"),
  startAccountScan: (accountId: string) =>
    request<ScanRun>(`/api/accounts/${accountId}/scan`, { method: "POST" }),
  startInventoryScan: () => request<ScanRun>("/api/scans/run-all", { method: "POST" }),
  getScanRuns: () => request<ScanRun[]>("/api/scans"),
  getScanRun: (runId: string) => request<ScanRun>(`/api/scans/${runId}`),
  getSettings: () => request<RuntimeSettings>("/api/settings"),
  updateSettings: (payload: RuntimeSettings) =>
    request<RuntimeSettings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  getPanelUsers: () => request<PanelUser[]>("/api/settings/access/users"),
  createPanelUser: (payload: { username: string; password: string; is_active: boolean }) =>
    request<PanelUser>("/api/settings/access/users", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updatePanelUser: (userId: string, payload: { is_active: boolean }) =>
    request<PanelUser>(`/api/settings/access/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  changeOwnPassword: (payload: { current_password: string; new_password: string }) =>
    request<{ message: string }>("/api/settings/access/change-password", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};
