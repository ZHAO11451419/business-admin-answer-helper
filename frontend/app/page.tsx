"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendChat, sendFeedback } from "@/lib/api";


type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  course: string;
  questionType: string;
  createdAt: string;
  feedback?: "positive" | "negative";
};

const COURSES = [
  "General Business",
  "Accounting",
  "Marketing",
  "Brand Strategy",
  "Franchising",
  "Human Resources",
  "Business Analytics",
  "Organizational Behavior",
  "Business Communication",
  "Business Law",
];

const TYPES = ["General", "Calculation", "Concept Explanation", "Case Study", "Essay", "Report Writing"];
const LANGUAGES = ["English", "Chinese", "Malay"];
const DETAILS = ["concise", "standard", "detailed"] as const;
const NEGATIVE_REASONS = ["Calculation", "Explanation", "Citation", "Structure", "Too generic", "Other"];

const starterPrompts = [
  {
    number: "01",
    title: "Explain a concept",
    text: "Explain the current ratio and how to interpret it in a business context.",
  },
  {
    number: "02",
    title: "Solve a calculation",
    text: "Calculate the break-even point in units when price is RM20, variable cost is RM12, and fixed costs are RM24,000.",
  },
  {
    number: "03",
    title: "Analyse a case",
    text: "Analyse the key branding issues in a rebranding case study and structure the answer as an academic response.",
  },
  {
    number: "04",
    title: "Build a report",
    text: "Give me an academic structure for a business report about sustainability reporting.",
  },
];

function newId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function displayTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Home() {
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [course, setCourse] = useState("General Business");
  const [questionType, setQuestionType] = useState("General");
  const [language, setLanguage] = useState("English");
  const [detail, setDetail] = useState<(typeof DETAILS)[number]>("standard");
  const [storeContent, setStoreContent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState<string | null>(null);
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [feedbackReason, setFeedbackReason] = useState(NEGATIVE_REASONS[0]);
  const [mobileNav, setMobileNav] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = localStorage.getItem("bah-session-id") || newId();
    localStorage.setItem("bah-session-id", id);
    setSessionId(id);

    const saved = localStorage.getItem("bah-messages");
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch {
        localStorage.removeItem("bah-messages");
      }
    }
  }, []);

  useEffect(() => {
    if (sessionId) localStorage.setItem("bah-messages", JSON.stringify(messages.slice(-40)));
  }, [messages, sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const recentQuestions = useMemo(
    () => messages.filter((m) => m.role === "user").slice(-5).reverse(),
    [messages],
  );

  function clearChat() {
    setMessages([]);
    localStorage.removeItem("bah-messages");
    setError("");
  }

  function previousUserMessage(messageId: string) {
    const index = messages.findIndex((item) => item.id === messageId);
    for (let i = index - 1; i >= 0; i -= 1) {
      if (messages[i]?.role === "user") return messages[i];
    }
    return undefined;
  }

  async function submit(override?: string) {
    const question = (override ?? input).trim();
    if (!question || loading || !sessionId) return;

    setInput("");
    setError("");
    setLoading(true);

    const userMessage: Message = {
      id: newId(),
      role: "user",
      content: question,
      course,
      questionType,
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      const history = [...messages, userMessage]
        .slice(-8)
        .slice(0, -1)
        .map((item) => ({ role: item.role, content: item.content }));

      const result = await sendChat({
        session_id: sessionId,
        message: question,
        course,
        question_type: questionType,
        language,
        detail,
        history,
        store_content: storeContent,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: result.message_id,
          role: "assistant",
          content: result.answer,
          course,
          questionType,
          createdAt: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function openNegativeFeedback(messageId: string) {
    setFeedbackReason(NEGATIVE_REASONS[0]);
    setFeedbackOpen(messageId);
  }

  async function submitFeedback(messageId: string, rating: "positive" | "negative", reason?: string) {
    const message = messages.find((item) => item.id === messageId);
    if (!message || !sessionId) return;

    setFeedbackBusy(true);
    setError("");

    const question = previousUserMessage(messageId);
    try {
      await sendFeedback({
        session_id: sessionId,
        message_id: messageId,
        rating,
        reason,
        course: message.course,
        question_type: message.questionType,
        store_content: storeContent,
        question_text: question?.content,
        answer_text: message.content,
      });

      setMessages((prev) => prev.map((item) => (item.id === messageId ? { ...item, feedback: rating } : item)));
      setFeedbackOpen(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save feedback.");
    } finally {
      setFeedbackBusy(false);
    }
  }

  function onInputKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  const hasChat = messages.length > 0;

  return (
    <main className="app-shell">
      <aside className={`sidebar ${mobileNav ? "mobile-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark">B</div>
          <div>
            <div className="brand-name">BAH</div>
            <div className="brand-subtitle">Business Academic Helper</div>
          </div>
        </div>

        <button className="new-chat-button" onClick={clearChat}>
          <span>＋</span> New chat
        </button>

        <div className="side-section">
          <div className="side-label">Recent questions</div>
          {recentQuestions.length ? (
            recentQuestions.map((item) => (
              <button key={item.id} className="history-item" onClick={() => void submit(item.content)}>
                <span className="history-dot" />
                <span>{item.content}</span>
              </button>
            ))
          ) : (
            <div className="empty-history">Your recent questions will appear here.</div>
          )}
        </div>

        <div className="sidebar-footer">
          <a href="/admin" className="footer-link">Admin dashboard</a>
          <div className="footer-note">Built for business students</div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setMobileNav((value) => !value)} aria-label="Open navigation">☰</button>
          <div>
            <div className="eyebrow">BUSINESS STUDY COPILOT</div>
            <h1>{hasChat ? "Study with BAH" : "Your business study copilot"}</h1>
          </div>
          <div className="topbar-actions">
            <button className="ghost-button" onClick={() => setSettingsOpen((value) => !value)}>
              Settings
            </button>
            <a className="avatar" href="#composer" aria-label="Jump to composer">B</a>
          </div>
        </header>

        <div className={`workspace-grid ${settingsOpen ? "with-panel" : ""}`}>
          <section className="chat-area">
            {!hasChat ? (
              <div className="welcome-screen">
                <div className="spark">✦</div>
                <h2>Write. Calculate. Analyse.</h2>
                <p>
                  Ask BAH about accounting, marketing, case studies, calculations,
                  reports, and business concepts.
                </p>

                <div className="prompt-grid">
                  {starterPrompts.map((item) => (
                    <button key={item.number} onClick={() => void submit(item.text)}>
                      <span>{item.number}</span>
                      <strong>{item.title}</strong>
                      <small>{item.text}</small>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="messages-wrap">
                {messages.map((message) => (
                  <article key={message.id} className={`message-row ${message.role}`}>
                    <div className="message-avatar">{message.role === "user" ? "Y" : "B"}</div>
                    <div className="message-main">
                      <div className="message-meta">
                        <div>
                          <strong>{message.role === "user" ? "You" : "BAH"}</strong>
                          <span className="message-tag">{message.course}</span>
                        </div>
                        <span>{displayTime(message.createdAt)}</span>
                      </div>

                      <div className={`message-bubble ${message.role === "assistant" ? "answer-bubble" : "user-bubble"}`}>
                        {message.role === "assistant" ? (
                          <div className="answer-text markdown-body">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                          </div>
                        ) : (
                          <div className="answer-text">{message.content}</div>
                        )}
                      </div>

                      {message.role === "assistant" && (
                        <div className="message-actions">
                          <button onClick={() => navigator.clipboard?.writeText(message.content)}>Copy</button>
                          <button
                            className={message.feedback === "positive" ? "active-action" : ""}
                            onClick={() => void submitFeedback(message.id, "positive")}
                          >
                            Helpful
                          </button>
                          <button
                            className={message.feedback === "negative" ? "active-action" : ""}
                            onClick={() => openNegativeFeedback(message.id)}
                          >
                            Needs work
                          </button>
                        </div>
                      )}
                    </div>
                  </article>
                ))}

                {loading && (
                  <article className="message-row assistant">
                    <div className="message-avatar">B</div>
                    <div className="message-main">
                      <div className="message-meta"><strong>BAH</strong><span>Thinking</span></div>
                      <div className="message-bubble answer-bubble loading-bubble"><span /><span /><span /></div>
                    </div>
                  </article>
                )}
                <div ref={bottomRef} />
              </div>
            )}

            {error && <div className="error-banner">{error}</div>}

            <div className="composer-wrap" id="composer">
              <div className="composer-box">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={onInputKeyDown}
                  placeholder="Ask a business question..."
                  maxLength={6000}
                  rows={1}
                />
                <div className="composer-bottom">
                  <div className="composer-left">
                    <button className="mini-select" onClick={() => setSettingsOpen(true)}>{course}</button>
                    <span className="composer-hint">Enter to send · Shift + Enter for a new line</span>
                  </div>
                  <button className="send-button" onClick={() => void submit()} disabled={!input.trim() || loading}>↗</button>
                </div>
              </div>
              <div className="privacy-mini">
                BAH can be used anonymously. Your question and answer are only stored for improvement when you enable content sharing in Settings.
              </div>
            </div>
          </section>

          {settingsOpen && (
            <aside className="settings-panel">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">ANSWER SETTINGS</div>
                  <h3>Shape the response</h3>
                </div>
                <button className="close-panel" onClick={() => setSettingsOpen(false)} aria-label="Close settings">×</button>
              </div>

              <label>
                Course
                <select value={course} onChange={(event) => setCourse(event.target.value)}>
                  {COURSES.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>

              <label>
                Question type
                <select value={questionType} onChange={(event) => setQuestionType(event.target.value)}>
                  {TYPES.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>

              <label>
                Language
                <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                  {LANGUAGES.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>

              <label>
                Detail
                <select value={detail} onChange={(event) => setDetail(event.target.value as (typeof DETAILS)[number])}>
                  {DETAILS.map((item) => <option key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</option>)}
                </select>
              </label>

              <div className="privacy-card">
                <div className="privacy-kicker">DATA CONTROL</div>
                <div className="privacy-title">Help improve BAH</div>
                <p>
                  Off by default: we keep only anonymous usage metrics. Turn it on when you agree to store the question and answer for model improvement.
                </p>
                <label className="toggle-row">
                  <span>Share content anonymously</span>
                  <input type="checkbox" checked={storeContent} onChange={(event) => setStoreContent(event.target.checked)} />
                </label>
              </div>

              <div className="settings-note">
                Your chat history remains in this browser. Server analytics do not store question/answer content unless you enable the option above.
              </div>
            </aside>
          )}
        </div>
      </section>

      {feedbackOpen && (
        <div className="modal-backdrop" onMouseDown={() => !feedbackBusy && setFeedbackOpen(null)}>
          <div className="feedback-modal" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-kicker">HELP US IMPROVE</div>
            <h3>What went wrong?</h3>
            <p>Choose the main issue with this answer.</p>
            <div className="reason-grid">
              {NEGATIVE_REASONS.map((reason) => (
                <button
                  key={reason}
                  className={feedbackReason === reason ? "reason-chip selected" : "reason-chip"}
                  onClick={() => setFeedbackReason(reason)}
                >
                  {reason}
                </button>
              ))}
            </div>
            <div className="modal-actions">
              <button className="ghost-button" onClick={() => setFeedbackOpen(null)} disabled={feedbackBusy}>Cancel</button>
              <button className="send-button submit-feedback" onClick={() => void submitFeedback(feedbackOpen, "negative", feedbackReason)} disabled={feedbackBusy}>
                {feedbackBusy ? "Saving…" : "Send feedback"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
