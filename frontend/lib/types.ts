export interface User {
  id: string;
  email: string;
  role: "admin" | "member";
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface SecretSummary {
  id: string;
  name: string;
  environment: string;
  description: string | null;
  tags: string[];
  owner_email: string;
  updated_at: string;
}

export interface SecretDetail extends SecretSummary {
  value: string;
}

export interface AuditEvent {
  id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown>;
  occurred_at: string;
  actor_email: string | null;
}

export interface AuthPayload {
  email: string;
  password: string;
}

export interface SecretPayload {
  name: string;
  value: string;
  environment: string;
  description: string | null;
  tags: string[];
}
