import { Check, Copy, Key, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { type CreatedToken, type TokenInfo, tokensApi } from "../api/client";

export function TokensPage() {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [created, setCreated] = useState<CreatedToken | null>(null);
  const [copied, setCopied] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);

  async function fetchTokens() {
    try {
      const res = await tokensApi.list();
      setTokens(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tokens.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchTokens();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const token = await tokensApi.create(newName.trim());
      setCreated(token);
      setNewName("");
      await fetchTokens();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create token.");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(keyId: string) {
    if (!confirm("Revoke this token? Any agent using it will stop working.")) return;
    setRevoking(keyId);
    try {
      await tokensApi.revoke(keyId);
      setTokens((prev) => prev.filter((t) => t.key_id !== keyId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke token.");
    } finally {
      setRevoking(null);
    }
  }

  async function copyToken(token: string) {
    await navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div style={{ maxWidth: 720, padding: "32px 24px" }}>
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Agent API Tokens</h2>
        <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>
          Create tokens for your local ADK agents to connect to this server.
          Set{" "}
          <code className="mono" style={{ fontSize: 12 }}>AGENTGUARD_API_KEY=&lt;token&gt;</code>
          {" "}and{" "}
          <code className="mono" style={{ fontSize: 12 }}>AGENTGUARD_BASE_URL=&lt;server-url&gt;</code>
          {" "}in your agent's environment.
        </p>
      </div>

      {/* Create token form */}
      <div className="card" style={{ marginBottom: 20, padding: 16 }}>
        <form onSubmit={handleCreate} style={{ display: "flex", gap: 10 }}>
          <input
            type="text"
            className="input"
            placeholder="Token name (e.g. my-laptop-agent)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            style={{ flex: 1 }}
          />
          <button
            type="submit"
            className="button button-primary"
            disabled={creating || !newName.trim()}
            style={{ whiteSpace: "nowrap" }}
          >
            <Plus size={14} />
            {creating ? "Creating…" : "Create token"}
          </button>
        </form>
      </div>

      {/* Newly created token — shown once */}
      {created && (
        <div
          className="card"
          style={{
            marginBottom: 20,
            padding: 16,
            border: "1px solid var(--allow)",
            background: "var(--allow-bg)",
          }}
        >
          <p style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 600, color: "var(--allow)" }}>
            Token created — copy it now. It won't be shown again.
          </p>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <code
              className="mono"
              style={{
                flex: 1,
                fontSize: 12,
                background: "var(--background)",
                border: "1px solid var(--border)",
                borderRadius: 4,
                padding: "8px 12px",
                wordBreak: "break-all",
              }}
            >
              {created.token}
            </code>
            <button
              type="button"
              className="button"
              onClick={() => copyToken(created.token)}
              style={{ flexShrink: 0 }}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <button
            type="button"
            onClick={() => setCreated(null)}
            style={{
              marginTop: 10,
              background: "none",
              border: "none",
              padding: 0,
              fontSize: 12,
              color: "var(--text-muted)",
              cursor: "pointer",
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <p style={{ color: "var(--block)", fontSize: 13, marginBottom: 16 }}>{error}</p>
      )}

      {/* Token list */}
      {loading ? (
        <div className="loading-state">Loading tokens…</div>
      ) : tokens.length === 0 ? (
        <div className="empty-state">
          <Key size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
          <p>No tokens yet. Create one above to connect your local agent.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {tokens.map((token) => (
            <div
              key={token.key_id}
              className="card"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
              }}
            >
              <Key size={16} style={{ color: "var(--brand-cyan)", flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{token.name}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                  <code className="mono">{token.key_id}</code>
                  {" · "}
                  Created {new Date(token.created_at).toLocaleDateString()}
                  {token.last_used_at && (
                    <> · Last used {new Date(token.last_used_at).toLocaleDateString()}</>
                  )}
                </div>
              </div>
              <button
                type="button"
                className="button button-danger"
                onClick={() => handleRevoke(token.key_id)}
                disabled={revoking === token.key_id}
                style={{ flexShrink: 0 }}
              >
                <Trash2 size={13} />
                {revoking === token.key_id ? "Revoking…" : "Revoke"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
