/** Shared API contracts between frontend and backend */

export type DeploymentStatus =
  | "pending"
  | "provisioning"
  | "hardening"
  | "installing"
  | "running"
  | "failed"
  | "destroyed";

export type CloudProvider = "hetzner" | "digitalocean";

export type LicenseTier = "starter" | "pro" | "enterprise";

export interface ApiError {
  detail: string;
  code?: string;
  request_id?: string;
}

export interface UserPublic {
  id: string;
  email: string;
  created_at: string;
}

export interface LicensePublic {
  id: string;
  key: string;
  tier: LicenseTier;
  active: boolean;
  expires_at: string | null;
}

export interface DeploymentPublic {
  id: string;
  provider: CloudProvider;
  region: string;
  server_name: string;
  ip_address: string | null;
  status: DeploymentStatus;
  monthly_cost: number | null;
  created_at: string;
}

export interface ScanIssue {
  severity: "critical" | "high" | "medium" | "low" | "info";
  description: string;
  remediation: string;
}

export interface ScanResult {
  score: number;
  grade: string;
  issues: ScanIssue[];
}

export interface AlertSettings {
  id: string;
  threshold: number;
  enabled: boolean;
}

export interface ProviderRegion {
  id: string;
  name: string;
  country?: string;
}

export interface ServerPlan {
  id: string;
  name: string;
  vcpus: number;
  memory_gb: number;
  disk_gb: number;
  monthly_cost_usd: number;
}
