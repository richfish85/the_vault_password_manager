"use client";

import { FormEvent, useCallback, useDeferredValue, useEffect, useState, useTransition } from "react";

import styles from "./vault-workspace.module.css";
import {
  createSecret,
  deleteSecret,
  getCurrentUser,
  getSecret,
  listAuditEvents,
  listSecrets,
  loginUser,
  logoutUser,
  registerUser,
  updateSecret,
} from "@/lib/api";
import type { AuditEvent, AuthPayload, SecretDetail, SecretPayload, SecretSummary, User } from "@/lib/types";

const TOKEN_KEY = "thevault.session";

const emptyAuthForm: AuthPayload = {
  email: "",
  password: "",
};

const emptySecretForm = {
  name: "",
  value: "",
  environment: "production",
  description: "",
  tags: "",
};

function parseTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-AU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatAction(action: string): string {
  return action
    .split(".")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toSecretPayload(form: typeof emptySecretForm): SecretPayload {
  return {
    name: form.name.trim(),
    value: form.value,
    environment: form.environment.trim() || "production",
    description: form.description.trim() || null,
    tags: parseTags(form.tags),
  };
}

export function VaultWorkspace() {
  const [mode, setMode] = useState<"register" | "login">("register");
  const [authForm, setAuthForm] = useState(emptyAuthForm);
  const [secretForm, setSecretForm] = useState(emptySecretForm);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [secrets, setSecrets] = useState<SecretSummary[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [selectedSecret, setSelectedSecret] = useState<SecretDetail | null>(null);
  const [editingSecretId, setEditingSecretId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const deferredFilter = useDeferredValue(filter);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const filteredSecrets = secrets.filter((secret) => {
    const query = deferredFilter.trim().toLowerCase();
    if (!query) {
      return true;
    }

    return [secret.name, secret.environment, secret.owner_email, secret.description ?? "", secret.tags.join(" ")]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  const refreshWorkspace = useCallback(async (activeToken: string, focusSecretId?: string | null) => {
    const [currentUser, secretItems, auditItems] = await Promise.all([
      getCurrentUser(activeToken),
      listSecrets(activeToken),
      listAuditEvents(activeToken),
    ]);

    setUser(currentUser);
    setSecrets(secretItems);
    setAuditEvents(auditItems);

    if (focusSecretId) {
      try {
        const revealed = await getSecret(activeToken, focusSecretId);
        setSelectedSecret(revealed);
      } catch {
        setSelectedSecret(null);
      }
    }
  }, []);

  useEffect(() => {
    const storedToken = window.localStorage.getItem(TOKEN_KEY);
    if (!storedToken) {
      return;
    }

    setToken(storedToken);
    void refreshWorkspace(storedToken).catch(() => {
      window.localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setUser(null);
    });
  }, [refreshWorkspace]);

  async function persistSession(activeToken: string): Promise<void> {
    window.localStorage.setItem(TOKEN_KEY, activeToken);
    setToken(activeToken);
    await refreshWorkspace(activeToken);
  }

  function resetEditor(): void {
    setSecretForm(emptySecretForm);
    setEditingSecretId(null);
  }

  function handleAuthSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setError(null);
    setNotice(null);

    startTransition(async () => {
      try {
        if (mode === "register") {
          await registerUser(authForm);
        }

        const session = await loginUser(authForm);
        await persistSession(session.access_token);
        setUser(session.user);
        setAuthForm(emptyAuthForm);
        setNotice(mode === "register" ? "Account created and signed in." : "Signed in.");
      } catch (submitError) {
        const message = submitError instanceof Error ? submitError.message : "Unable to authenticate.";
        setError(message);
      }
    });
  }

  function handleSecretSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!token) {
      return;
    }

    setError(null);
    setNotice(null);

    startTransition(async () => {
      try {
        const payload = toSecretPayload(secretForm);
        if (editingSecretId) {
          await updateSecret(token, editingSecretId, payload);
          await refreshWorkspace(token, editingSecretId);
          setNotice("Secret updated.");
        } else {
          const created = await createSecret(token, payload);
          await refreshWorkspace(token, created.id);
          setNotice("Secret stored.");
        }
        resetEditor();
      } catch (submitError) {
        const message = submitError instanceof Error ? submitError.message : "Unable to save the secret.";
        setError(message);
      }
    });
  }

  function handleReveal(secretId: string): void {
    if (!token) {
      return;
    }

    setError(null);
    setNotice(null);

    startTransition(async () => {
      try {
        const revealed = await getSecret(token, secretId);
        setSelectedSecret(revealed);
        setNotice(`Decrypted ${revealed.name}.`);
        await refreshWorkspace(token, secretId);
      } catch (requestError) {
        const message = requestError instanceof Error ? requestError.message : "Unable to decrypt the secret.";
        setError(message);
      }
    });
  }

  function handleEditSelected(): void {
    if (!selectedSecret) {
      return;
    }

    setEditingSecretId(selectedSecret.id);
    setSecretForm({
      name: selectedSecret.name,
      value: selectedSecret.value,
      environment: selectedSecret.environment,
      description: selectedSecret.description ?? "",
      tags: selectedSecret.tags.join(", "),
    });
    setNotice(`Loaded ${selectedSecret.name} into the editor.`);
  }

  function handleDelete(secretId: string): void {
    if (!token) {
      return;
    }

    const target = secrets.find((secret) => secret.id === secretId);
    if (!target) {
      return;
    }

    const confirmed = window.confirm(`Delete ${target.name}? This cannot be undone.`);
    if (!confirmed) {
      return;
    }

    setError(null);
    setNotice(null);

    startTransition(async () => {
      try {
        await deleteSecret(token, secretId);
        if (selectedSecret?.id === secretId) {
          setSelectedSecret(null);
        }
        if (editingSecretId === secretId) {
          resetEditor();
        }
        await refreshWorkspace(token);
        setNotice(`${target.name} deleted.`);
      } catch (requestError) {
        const message = requestError instanceof Error ? requestError.message : "Unable to delete the secret.";
        setError(message);
      }
    });
  }

  function handleLogout(): void {
    if (!token) {
      return;
    }

    startTransition(async () => {
      try {
        await logoutUser(token);
      } catch {
        // Best effort revoke; local teardown still matters.
      } finally {
        window.localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
        setSecrets([]);
        setAuditEvents([]);
        setSelectedSecret(null);
        resetEditor();
        setNotice("Signed out.");
      }
    });
  }

  return (
    <main className={styles.shell}>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.eyebrow}>TheVault</span>
          <h1>Secure secrets management with an interview-ready architecture.</h1>
          <p>
            React + TypeScript on the client. FastAPI in front of auth, encrypted secret storage, and audit
            tracking. Postgres remains the source of truth and Redis handles rate limiting plus token revocation.
          </p>
        </div>
        <div className={styles.heroBadges}>
          <span>JWT + RBAC</span>
          <span>AES-encrypted values</span>
          <span>Postgres + Redis</span>
          <span>Audit-first workflows</span>
        </div>
      </section>

      {error ? <div className={styles.alertError}>{error}</div> : null}
      {notice ? <div className={styles.alertNotice}>{notice}</div> : null}

      <section className={styles.topGrid}>
        <article className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.panelLabel}>{user ? "Session" : "Access"}</p>
              <h2>{user ? `Signed in as ${user.email}` : "Create or resume a vault session"}</h2>
            </div>
            {user ? (
              <span className={styles.roleBadge} data-role={user.role}>
                {user.role}
              </span>
            ) : null}
          </div>

          {user ? (
            <div className={styles.sessionCard}>
              <div className={styles.metricRow}>
                <div>
                  <span>Secrets visible</span>
                  <strong>{secrets.length}</strong>
                </div>
                <div>
                  <span>Audit entries</span>
                  <strong>{auditEvents.length}</strong>
                </div>
              </div>
              <p className={styles.supportingText}>
                {user.role === "admin"
                  ? "You can inspect every secret and every audit event in the workspace."
                  : "You can manage your own secrets, decrypt them on demand, and review your own audit history."}
              </p>
              <button className={styles.secondaryButton} onClick={handleLogout} type="button">
                Revoke session
              </button>
            </div>
          ) : (
            <form className={styles.form} onSubmit={handleAuthSubmit}>
              <div className={styles.modeSwitch}>
                <button
                  className={mode === "register" ? styles.modeActive : styles.modeButton}
                  onClick={() => setMode("register")}
                  type="button"
                >
                  Register
                </button>
                <button
                  className={mode === "login" ? styles.modeActive : styles.modeButton}
                  onClick={() => setMode("login")}
                  type="button"
                >
                  Login
                </button>
              </div>

              <label className={styles.field}>
                <span>Email</span>
                <input
                  onChange={(event) => setAuthForm((current) => ({ ...current, email: event.target.value }))}
                  placeholder="security@teamvault.dev"
                  type="email"
                  value={authForm.email}
                />
              </label>

              <label className={styles.field}>
                <span>Password</span>
                <input
                  minLength={12}
                  onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))}
                  placeholder="Use at least 12 characters"
                  type="password"
                  value={authForm.password}
                />
              </label>

              <button className={styles.primaryButton} disabled={isPending} type="submit">
                {isPending ? "Working..." : mode === "register" ? "Create account" : "Sign in"}
              </button>
            </form>
          )}
        </article>

        <article className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.panelLabel}>Architecture</p>
              <h2>Security controls are visible in the product surface.</h2>
            </div>
          </div>
          <div className={styles.architectureGrid}>
            <div className={styles.archCard}>
              <span>Frontend</span>
              <strong>React + TypeScript</strong>
              <p>Single dashboard for auth, secret CRUD, and audit review.</p>
            </div>
            <div className={styles.archCard}>
              <span>Backend</span>
              <strong>FastAPI</strong>
              <p>CORS, JWT validation, Redis-backed rate limiting, and route-level RBAC.</p>
            </div>
            <div className={styles.archCard}>
              <span>Secrets</span>
              <strong>AES encryption</strong>
              <p>Secret payloads are encrypted before they ever touch Postgres.</p>
            </div>
            <div className={styles.archCard}>
              <span>Observability</span>
              <strong>Audit log</strong>
              <p>Authentication and secret operations are recorded with IP context.</p>
            </div>
          </div>
        </article>
      </section>

      <section className={styles.workspaceGrid}>
        <article className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.panelLabel}>Secret Editor</p>
              <h2>{editingSecretId ? "Update an existing secret" : "Store a new secret"}</h2>
            </div>
            {editingSecretId ? (
              <button className={styles.ghostButton} onClick={resetEditor} type="button">
                Clear
              </button>
            ) : null}
          </div>

          <form className={styles.form} onSubmit={handleSecretSubmit}>
            <label className={styles.field}>
              <span>Name</span>
              <input
                disabled={!user}
                onChange={(event) => setSecretForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Stripe production API key"
                value={secretForm.name}
              />
            </label>

            <label className={styles.field}>
              <span>Value</span>
              <textarea
                disabled={!user}
                onChange={(event) => setSecretForm((current) => ({ ...current, value: event.target.value }))}
                placeholder="sk_live_..."
                rows={5}
                value={secretForm.value}
              />
            </label>

            <div className={styles.splitFields}>
              <label className={styles.field}>
                <span>Environment</span>
                <input
                  disabled={!user}
                  onChange={(event) => setSecretForm((current) => ({ ...current, environment: event.target.value }))}
                  placeholder="production"
                  value={secretForm.environment}
                />
              </label>

              <label className={styles.field}>
                <span>Tags</span>
                <input
                  disabled={!user}
                  onChange={(event) => setSecretForm((current) => ({ ...current, tags: event.target.value }))}
                  placeholder="payments, api, critical"
                  value={secretForm.tags}
                />
              </label>
            </div>

            <label className={styles.field}>
              <span>Description</span>
              <textarea
                disabled={!user}
                onChange={(event) => setSecretForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Rotation notes, owner context, or rollout comments"
                rows={3}
                value={secretForm.description}
              />
            </label>

            <button className={styles.primaryButton} disabled={!user || isPending} type="submit">
              {editingSecretId ? "Update secret" : "Store secret"}
            </button>
          </form>
        </article>

        <article className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.panelLabel}>Vault Inventory</p>
              <h2>Encrypted secrets</h2>
            </div>
            <span className={styles.statBadge}>{filteredSecrets.length}</span>
          </div>

          <label className={styles.searchField}>
            <span>Filter</span>
            <input
              onChange={(event) => setFilter(event.target.value)}
              placeholder="Search name, owner, environment, tags"
              value={filter}
            />
          </label>

          <div className={styles.list}>
            {filteredSecrets.length ? (
              filteredSecrets.map((secret) => (
                <div className={styles.listItem} key={secret.id}>
                  <div>
                    <strong>{secret.name}</strong>
                    <p>{secret.description ?? "Encrypted item with no notes attached yet."}</p>
                    <div className={styles.metaRow}>
                      <span>{secret.environment}</span>
                      <span>{secret.owner_email}</span>
                      <span>{formatTimestamp(secret.updated_at)}</span>
                    </div>
                    <div className={styles.tagRow}>
                      {secret.tags.map((tag) => (
                        <span className={styles.tag} key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className={styles.actionRow}>
                    <button className={styles.secondaryButton} onClick={() => handleReveal(secret.id)} type="button">
                      Reveal
                    </button>
                    <button className={styles.dangerButton} onClick={() => handleDelete(secret.id)} type="button">
                      Delete
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className={styles.emptyState}>
                {user
                  ? "No secrets match the current filter."
                  : "Authenticate to start creating and decrypting secrets."}
              </div>
            )}
          </div>
        </article>

        <article className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.panelLabel}>Reveal + Audit</p>
              <h2>Decrypted view and event trail</h2>
            </div>
          </div>

          <div className={styles.detailCard}>
            {selectedSecret ? (
              <>
                <div className={styles.detailHeader}>
                  <div>
                    <strong>{selectedSecret.name}</strong>
                    <p>{selectedSecret.description ?? "No description provided."}</p>
                  </div>
                  <button className={styles.secondaryButton} onClick={handleEditSelected} type="button">
                    Edit
                  </button>
                </div>
                <div className={styles.detailMeta}>
                  <span>{selectedSecret.environment}</span>
                  <span>{selectedSecret.owner_email}</span>
                </div>
                <pre className={styles.secretValue}>
                  <code>{selectedSecret.value}</code>
                </pre>
              </>
            ) : (
              <div className={styles.emptyState}>Reveal a secret to inspect its decrypted value.</div>
            )}
          </div>

          <div className={styles.auditList}>
            {auditEvents.length ? (
              auditEvents.map((eventItem) => (
                <div className={styles.auditItem} key={eventItem.id}>
                  <div>
                    <strong>{formatAction(eventItem.action)}</strong>
                    <p>
                      {eventItem.actor_email ?? "System"} · {formatTimestamp(eventItem.occurred_at)}
                    </p>
                  </div>
                  <span className={styles.auditTarget}>{eventItem.target_type}</span>
                </div>
              ))
            ) : (
              <div className={styles.emptyState}>Audit events will appear once actions start hitting the API.</div>
            )}
          </div>
        </article>
      </section>
    </main>
  );
}
