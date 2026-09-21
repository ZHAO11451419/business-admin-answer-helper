"use client";

import { useState } from "react";
import { downloadAdminExport, fetchAdminOverview } from "@/lib/api";

export default function AdminPage() {
  const [key, setKey] = useState("");
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      setData(await fetchAdminOverview(key));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  async function exportCsv() {
    try {
      const blob = await downloadAdminExport(key);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "bah_usage_events.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to export data.");
    }
  }

  return (
    <main className="admin-shell">
      <div className="admin-header">
        <div>
          <div className="eyebrow">BAH OPERATIONS</div>
          <h1>Product analytics</h1>
          <p>Usage, feedback, course distribution, and model-improvement signals.</p>
        </div>
        <a className="ghost-button" href="/">Back to BAH</a>
      </div>

      {!data ? (
        <section className="admin-login-card">
          <div className="admin-lock">⌁</div>
          <h2>Admin access</h2>
          <p>Enter the server-side ADMIN_KEY. This value is sent only to the backend as an authorization header.</p>
          <input type="password" value={key} onChange={(event) => setKey(event.target.value)} placeholder="ADMIN_KEY" />
          <button className="send-button wide" onClick={() => void loadDashboard()} disabled={!key || loading}>
            {loading ? "Checking…" : "Open dashboard"}
          </button>
          {error && <div className="error-banner">{error}</div>}
        </section>
      ) : (
        <>
          <section className="stats-grid">
            {[
              ["Requests", data.overview?.requests ?? 0],
              ["Unique sessions", data.overview?.unique_sessions ?? 0],
              ["Positive feedback", data.overview?.positive_feedback ?? 0],
              ["Negative feedback", data.overview?.negative_feedback ?? 0],
              ["Avg latency", `${Math.round(Number(data.overview?.avg_latency_ms ?? 0))} ms`],
            ].map(([label, value]) => (
              <div className="stat-card" key={String(label)}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </section>

          <section className="admin-grid">
            <div className="admin-card">
              <div className="card-title"><h2>Courses</h2><span>Chat share</span></div>
              <div className="reason-list">
                {(data.course_breakdown || []).map((item: any) => (
                  <div className="reason-row" key={item.course}>
                    <div><strong>{item.course || "Unspecified"}</strong><span>{item.count}</span></div>
                    <div className="bar"><i style={{ width: `${Math.min(100, Number(item.percentage || 0))}%` }} /></div>
                  </div>
                ))}
              </div>
            </div>

            <div className="admin-card">
              <div className="card-title"><h2>Negative feedback</h2><span>Why users disliked an answer</span></div>
              <div className="reason-list">
                {(data.feedback_reasons || []).map((item: any) => (
                  <div className="reason-row" key={item.reason}>
                    <div><strong>{item.reason || "Unspecified"}</strong><span>{item.count}</span></div>
                    <div className="bar"><i style={{ width: `${Math.min(100, Number(item.percentage || 0))}%` }} /></div>
                  </div>
                ))}
              </div>
            </div>

            <div className="admin-card wide-card">
              <div className="card-title"><h2>Recent daily usage</h2><span>Last 14 days</span></div>
              <div className="daily-table">
                <div className="daily-row header"><span>Date</span><span>Chats</span><span>Sessions</span><span>Avg ms</span></div>
                {(data.daily_usage || []).map((item: any) => (
                  <div className="daily-row" key={item.day}>
                    <span>{item.day}</span><span>{item.chats}</span><span>{item.sessions}</span><span>{Math.round(Number(item.avg_latency_ms || 0))}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="admin-toolbar">
            <div>
              <strong>Export feedback data</strong>
              <span>CSV includes content only for users who opted in.</span>
            </div>
            <button className="ghost-button" onClick={() => void exportCsv()}>Export CSV</button>
          </section>

          {error && <div className="error-banner">{error}</div>}
        </>
      )}
    </main>
  );
}
