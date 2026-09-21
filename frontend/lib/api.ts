const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export type HistoryItem = {
  role: "user" | "assistant";
  content: string;
};

export type ChatPayload = {
  session_id: string;
  message: string;
  course: string;
  question_type: string;
  language: string;
  detail: "concise" | "standard" | "detailed";
  history: HistoryItem[];
  store_content: boolean;
};

async function parseResponse(response: Response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : "Request failed.");
  }
  return data;
}

export async function sendChat(payload: ChatPayload) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response) as Promise<{
    message_id: string;
    answer: string;
    model_version: string;
    latency_ms: number;
    meta?: { calculator_corrections?: number };
  }>;
}

export async function sendFeedback(payload: {
  session_id: string;
  message_id: string;
  rating: "positive" | "negative";
  reason?: string;
  course?: string;
  question_type?: string;
  store_content: boolean;
  question_text?: string;
  answer_text?: string;
}) {
  const response = await fetch(`${API_BASE}/api/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function fetchAdminOverview(adminKey: string) {
  const response = await fetch(`${API_BASE}/api/admin/overview`, {
    headers: { "X-Admin-Key": adminKey },
    cache: "no-store",
  });
  return parseResponse(response);
}

export async function downloadAdminExport(adminKey: string) {
  const response = await fetch(`${API_BASE}/api/admin/export`, {
    headers: { "X-Admin-Key": adminKey },
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data?.detail === "string" ? data.detail : "Unable to export data.");
  }
  return response.blob();
}
