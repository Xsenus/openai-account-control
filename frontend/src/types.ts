export type AuthSession = {
  auth_enabled: boolean;
  authenticated: boolean;
  user_id: string | null;
  username: string | null;
  issued_at: string | null;
  expires_at: string | null;
};

export type PanelUser = {
  id: string;
  username: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountDraft = {
  label: string;
  email_hint: string | null;
  notes: string;
  is_enabled: boolean;
};

export type Account = AccountDraft & {
  id: string;
  auth_method: string;
  has_session_state: boolean;
  last_auth_at: string | null;
  last_scan_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CodexUsagePeriod = {
  period: string;
  percent_remaining: string | null;
  total: string | null;
  used: string | null;
  remaining: string | null;
  refresh_text: string | null;
  reset_at: string | null;
  source_text: string | null;
  confidence: string;
};

export type TeamInvitation = {
  status: string;
  label: string | null;
  source_text: string | null;
  confidence: string;
};

export type WorkspaceSnapshot = {
  id: string;
  account_id: string;
  workspace_name: string;
  workspace_kind: string;
  workspace_state: string;
  overall_status: string;
  role: string | null;
  seat_type: string | null;
  personal_plan: string | null;
  codex_limit_unit: string | null;
  included_limit_text: string | null;
  included_usage_percent_remaining: string | null;
  included_usage_total: string | null;
  included_usage_used: string | null;
  included_usage_remaining: string | null;
  included_usage_refresh_text: string | null;
  codex_usage: Record<string, CodexUsagePeriod>;
  team_invitation: TeamInvitation | null;
  credits_balance: string | null;
  auto_topup_enabled: boolean | null;
  spend_limit: string | null;
  source: string;
  checked_at: string;
  evidence_dir: string | null;
  raw_payload: Record<string, unknown>;
};

export type ScanRun = {
  id: string;
  account_id: string | null;
  scope: string;
  status: string;
  manual: boolean;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  metrics: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DashboardCounters = {
  total_accounts: number;
  active_accounts: number;
  with_valid_session: number;
  workspaces_ok: number;
  workspaces_low: number;
  workspaces_blocked: number;
  workspaces_deactivated: number;
  workspaces_partial: number;
  last_scan_at: string | null;
};

export type DashboardSummary = {
  counters: DashboardCounters;
  latest_snapshots: WorkspaceSnapshot[];
  latest_runs: ScanRun[];
};

export type RuntimeSettings = {
  scan_interval_minutes: number;
  low_credits_threshold: number;
  low_usage_percent_threshold: number;
};

export type AuthJob = {
  job_id: string;
  account_id: string;
  status: string;
  message: string;
  started_at: string | null;
  finished_at: string | null;
};
