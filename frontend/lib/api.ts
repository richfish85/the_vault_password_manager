import type {
  AuditEvent,
  AuthPayload,
  SecretDetail,
  SecretPayload,
  SecretSummary,
  TokenResponse,
  User,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? "Request failed.", response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function registerUser(payload: AuthPayload): Promise<User> {
  return request<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginUser(payload: AuthPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logoutUser(token: string): Promise<void> {
  await request<void>("/auth/logout", {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function getCurrentUser(token: string): Promise<User> {
  return request<User>("/auth/me", {
    headers: authHeaders(token),
  });
}

export async function listSecrets(token: string): Promise<SecretSummary[]> {
  return request<SecretSummary[]>("/secrets", {
    headers: authHeaders(token),
  });
}

export async function getSecret(token: string, secretId: string): Promise<SecretDetail> {
  return request<SecretDetail>(`/secrets/${secretId}`, {
    headers: authHeaders(token),
  });
}

export async function createSecret(token: string, payload: SecretPayload): Promise<SecretSummary> {
  return request<SecretSummary>("/secrets", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateSecret(
  token: string,
  secretId: string,
  payload: SecretPayload,
): Promise<SecretSummary> {
  return request<SecretSummary>(`/secrets/${secretId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteSecret(token: string, secretId: string): Promise<void> {
  await request<void>(`/secrets/${secretId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export async function listAuditEvents(token: string): Promise<AuditEvent[]> {
  return request<AuditEvent[]>("/audit", {
    headers: authHeaders(token),
  });
}
