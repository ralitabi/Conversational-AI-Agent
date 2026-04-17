import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BenefitsCalculatorCard from "./BenefitsCalculatorCard";
import FeedbackStars from "./FeedbackStars";

// ─── Constants ────────────────────────────────────────────────────────────────
const REMINDER_MS = 30_000;
const CLOSE_MS    = 45_000;

/** Return a random delay in ms between min and max (inclusive). */
const randDelay = (min = 120, max = 220) =>
  Math.floor(Math.random() * (max - min + 1)) + min;

// ─── Rich-text helpers ────────────────────────────────────────────────────────
/**
 * Convert inline markdown-like syntax and bare URLs to safe HTML fragments.
 * Only called on plain-text content — never on already-HTML strings.
 */
function formatInline(text) {
  return text
    // **bold** and __bold__
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.*?)__/g, "<strong>$1</strong>")
    // *italic*
    .replace(/\*([^*\n]+?)\*/g, "<em>$1</em>")
    // Bare URLs → clickable links (before phone so URLs with numbers aren't caught)
    .replace(
      /(https?:\/\/[^\s<>"')\]]+)/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer" style="word-break:break-all">$1</a>'
    )
    // UK phone numbers → tel: links  e.g. 01274 438723 / 0800 123 4567 / +44 1274 438723
    .replace(
      /(\+?44[\s-]?|0)(\d[\d\s-]{6,11}\d)/g,
      (match) => {
        const digits = match.replace(/[\s-]/g, "");
        const tel = digits.startsWith("44") ? "+" + digits : digits;
        return `<a href="tel:${tel}" style="font-weight:600;text-decoration:underline">${match}</a>`;
      }
    );
}

/**
 * Convert a plain-text assistant reply to clean HTML.
 * - Handles **bold**, URLs → links, dash/bullet lists, paragraph spacing.
 * - Never touches strings that already contain HTML tags.
 */
function richTextToHtml(text) {
  if (!text) return "";
  // Already HTML — leave untouched
  if (/<[a-z][\s\S]*?>/i.test(text)) return text;

  const lines  = text.split("\n");
  const output = [];
  let inUl = false;

  const closeList = () => { if (inUl) { output.push("</ul>"); inUl = false; } };

  for (let i = 0; i < lines.length; i++) {
    const raw     = lines[i];
    const trimmed = raw.trim();

    if (!trimmed) {
      closeList();
      // Blank line between paragraphs — only add spacing if next line has content
      const next = lines.slice(i + 1).find((l) => l.trim());
      if (next) output.push('<div class="mt-2"></div>');
      continue;
    }

    // Bullet / dash list item: -, •, or *
    const bullet = trimmed.match(/^[-•]\s+(.+)$/);
    if (bullet) {
      if (!inUl) { output.push('<ul class="my-1 space-y-1 pl-4 list-disc">'); inUl = true; }
      output.push(`<li class="leading-6">${formatInline(bullet[1])}</li>`);
      continue;
    }

    // Numbered list item: "1. text" — render as a bullet, not a section header
    const numbered = trimmed.match(/^\d+\.\s+(.+)$/);
    if (numbered) {
      if (!inUl) { output.push('<ul class="my-1 space-y-1 pl-4 list-disc">'); inUl = true; }
      output.push(`<li class="leading-6">${formatInline(numbered[1])}</li>`);
      continue;
    }

    // Regular text line
    closeList();
    output.push(`<p class="leading-7">${formatInline(trimmed)}</p>`);
  }

  closeList();
  return output.join("");
}

/**
 * Split a long plain-text string into 2–3 bubbles at paragraph boundaries.
 * Lists are never split mid-list. HTML cards are returned as-is.
 */
function splitIntoBubbles(text) {
  if (!text) return [text];

  // HTML cards — never split
  if (/<[a-z][\s\S]*?>/i.test(text)) return [text];

  // Short — no split needed
  if (text.length <= 200) return [text];

  // If predominantly a list, keep as one bubble
  const lines     = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const listLines = lines.filter((l) => /^[-•\d]/.test(l));
  if (listLines.length / lines.length >= 0.4) return [text];

  // Split at double-newline paragraph breaks
  const paras = text.split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
  if (paras.length >= 2) {
    // Merge into at most 3 bubbles
    if (paras.length <= 3) return paras;
    const mid = Math.ceil(paras.length / 2);
    return [
      paras.slice(0, mid).join("\n\n"),
      paras.slice(mid).join("\n\n"),
    ].filter(Boolean);
  }

  // No paragraph breaks — split at sentence boundary near the halfway point
  const sentences = text.match(/[^.!?]+[.!?]["']?\s*/g);
  if (!sentences || sentences.length <= 2) return [text];
  const mid = Math.ceil(sentences.length / 2);
  return [
    sentences.slice(0, mid).join("").trim(),
    sentences.slice(mid).join("").trim(),
  ].filter(Boolean);
}

const API_URL = process.env.NODE_ENV === "production"
  ? "/chat"
  : (process.env.REACT_APP_API_URL || "http://127.0.0.1:8000/chat");

// ─── Small reusable avatars ───────────────────────────────────────────────────
function AssistantAvatar() {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#dbeafe] text-[#0f4ca3] shadow-sm">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="8" r="3.2" />
        <path d="M5.5 19c1.4-3 4-4.5 6.5-4.5S17 16 18.5 19" />
      </svg>
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#0f4ca3] text-white shadow-sm">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="8" r="3.2" />
        <path d="M5.5 19c1.4-3 4-4.5 6.5-4.5S17 16 18.5 19" />
      </svg>
    </div>
  );
}

// ─── Send icon ────────────────────────────────────────────────────────────────
function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 2L11 13" />
      <path d="M22 2L15 22 11 13 2 9l20-7z" />
    </svg>
  );
}

// ─── Typing indicator ────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <div className="fade-slide-in flex items-end gap-3">
      <AssistantAvatar />
      <div className="rounded-[1.5rem] rounded-tl-md bg-white px-5 py-3.5 shadow-sm">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.3s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.15s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300" />
          <span className="ml-2 text-xs font-medium text-slate-400">Bradford Council is typing…</span>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────
export default function ChatModal({ chatOpen, setChatOpen, starterQueries = [] }) {
  const [selectedQuery, setSelectedQuery]     = useState("");
  const [messages, setMessages]               = useState([]);
  const [input, setInput]                     = useState("");
  const [isTyping, setIsTyping]               = useState(false);
  const [sessionId, setSessionId]             = useState(() => crypto.randomUUID());
  const [pendingOptions, setPendingOptions]   = useState([]);
  const [pendingInputType, setPendingInputType] = useState(null);
  const [showScrollBtn, setShowScrollBtn]     = useState(false);

  const messagesEndRef     = useRef(null);
  const scrollContainerRef = useRef(null);
  const addressBoxRef      = useRef(null);
  const reminderTimerRef   = useRef(null);
  const closeTimerRef      = useRef(null);
  const hasShownReminderRef  = useRef(false);
  const hasShownClosureRef   = useRef(false);

  // ── Intro messages ──────────────────────────────────────────────────────────
  const introMessages = useMemo(() => {
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return [
      {
        role: "assistant",
        title: "Hello, welcome to Bradford Council Assistant.",
        text: "I can help you find the right council service, explain the next steps, and guide you to the correct contact or online page.",
        time: now,
        isHtml: false,
      },
      {
        role: "assistant",
        title: "What would you like help with today?",
        text: "Choose one of the service areas below, or type your question.",
        time: now,
        isHtml: false,
      },
    ];
  }, []);

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const wait     = (ms) => new Promise((r) => setTimeout(r, ms));
  const getTime  = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const containsHtml = useCallback((text) => /<\/?[a-z][\s\S]*>/i.test(String(text || "")), []);

  const isSelectableInputType = useCallback(
    (t) => t === "options" || t === "address_list",
    []
  );

  const normaliseOption = useCallback((option) => {
    if (typeof option === "string") {
      const t = option.trim();
      return { id: t, value: t, label: t, text: t, band: "" };
    }
    const id    = String(option?.id ?? option?.uprn ?? option?.value ?? "").trim();
    const label = String(option?.label ?? option?.text ?? id).trim();
    return {
      ...option,
      id,
      value: id,
      label,
      text: label,
      band: String(option?.band ?? "").trim(),
      url: String(option?.url ?? "").trim(),
      display_index:
        typeof option?.display_index === "number" || typeof option?.display_index === "string"
          ? option.display_index
          : null,
    };
  }, []);

  const isLikelyClosingMessage = useCallback((value) => {
    const cleaned = String(value || "")
      .toLowerCase()
      .trim()
      .replace(/[^\w\s]/g, "")
      .replace(/\s+/g, " ");
    return new Set([
      "ok","okay","ok thanks","okay thanks","thanks","thank you",
      "ok thank you","okay thank you","thats all","that's all",
      "thats it","that's it","all good","im done","i am done",
      "nothing else","cheers","done thanks","no thanks","no thank you",
    ]).has(cleaned);
  }, []);

  // ── Message append helpers ──────────────────────────────────────────────────
  const appendUserMessage = useCallback((text) => {
    setMessages((prev) => [...prev, { role: "user", text, time: getTime(), isHtml: false }]);
  }, []);

  const appendAssistantMessage = useCallback((text, isHtml = false) => {
    setMessages((prev) => [...prev, { role: "assistant", text, time: getTime(), isHtml }]);
  }, []);

  // ── Timer helpers ───────────────────────────────────────────────────────────
  const clearReminderTimer = useCallback(() => {
    if (reminderTimerRef.current) { clearTimeout(reminderTimerRef.current); reminderTimerRef.current = null; }
  }, []);

  const clearCloseTimer = useCallback(() => {
    if (closeTimerRef.current) { clearTimeout(closeTimerRef.current); closeTimerRef.current = null; }
  }, []);

  const clearInactivityTimers = useCallback(() => {
    clearReminderTimer();
    clearCloseTimer();
  }, [clearReminderTimer, clearCloseTimer]);

  const resetInactivityFlags = useCallback(() => {
    hasShownReminderRef.current = false;
    hasShownClosureRef.current  = false;
  }, []);

  const stopInactivityFlow = useCallback(() => {
    clearInactivityTimers();
    resetInactivityFlags();
  }, [clearInactivityTimers, resetInactivityFlags]);

  const clearPendingUi = useCallback(() => {
    setPendingOptions([]);
    setPendingInputType(null);
  }, []);

  const beginInactivityFlow = useCallback(() => {
    clearInactivityTimers();
    if (
      isTyping ||
      isSelectableInputType(pendingInputType) ||
      pendingInputType === "calculator" ||
      pendingInputType === "feedback" ||
      pendingOptions.length > 0 ||
      hasShownClosureRef.current
    ) return;

    reminderTimerRef.current = setTimeout(() => {
      if (hasShownReminderRef.current || hasShownClosureRef.current) return;
      appendAssistantMessage("Is there anything else you need to ask?");
      hasShownReminderRef.current = true;
    }, REMINDER_MS);

    closeTimerRef.current = setTimeout(() => {
      if (hasShownClosureRef.current) return;
      appendAssistantMessage("Thank you for using the Bradford Council Assistant. Have a great day!");
      hasShownClosureRef.current = true;
      clearInactivityTimers();
    }, CLOSE_MS);
  }, [
    appendAssistantMessage, clearInactivityTimers, isSelectableInputType,
    isTyping, pendingInputType, pendingOptions.length,
  ]);

  // ── Chat actions ────────────────────────────────────────────────────────────
  const restartChat = () => {
    setSelectedQuery("");
    setMessages([]);
    setInput("");
    setIsTyping(false);
    setPendingOptions([]);
    setPendingInputType(null);
    stopInactivityFlow();
    setSessionId(crypto.randomUUID());
  };

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, []);

  // ── Effects ─────────────────────────────────────────────────────────────────
  // Inject keyframe CSS once
  useEffect(() => {
    const styleId = "chat-fade-keyframes";
    if (document.getElementById(styleId)) return;
    const style = document.createElement("style");
    style.id = styleId;
    style.innerHTML = `
      @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      .fade-slide-in { animation: fadeSlideIn 0.28s ease-out; }
      .address-scrollbox { scrollbar-width: thin; scrollbar-color: #b8c7e0 transparent; }
      .address-scrollbox::-webkit-scrollbar { width: 6px; }
      .address-scrollbox::-webkit-scrollbar-thumb { background: #b8c7e0; border-radius: 999px; }
      .address-scrollbox::-webkit-scrollbar-thumb:hover { background: #9fb3d4; }
    `;
    document.head.appendChild(style);
  }, []);

  // Auto-scroll when messages change
  useEffect(() => {
    if (!chatOpen) return;
    const t = setTimeout(() => scrollToBottom(), 80);
    return () => clearTimeout(t);
  }, [chatOpen, messages, isTyping, pendingOptions, scrollToBottom]);

  // Scroll-to-top of options box when new options arrive
  useEffect(() => {
    if (isSelectableInputType(pendingInputType) && pendingOptions.length > 0) {
      addressBoxRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [isSelectableInputType, pendingInputType, pendingOptions]);

  // Show/hide scroll-to-bottom button
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const onScroll = () => {
      const distFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
      setShowScrollBtn(distFromBottom > 120);
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    return () => container.removeEventListener("scroll", onScroll);
  }, []);

  // Cleanup timers on unmount
  useEffect(() => () => clearInactivityTimers(), [clearInactivityTimers]);

  // ── Send message ────────────────────────────────────────────────────────────
  const sendMessage = async (customMessage = null, visibleText = null) => {
    const textToSend = String(customMessage ?? input).trim();
    if (!textToSend || isTyping) return;

    clearInactivityTimers();
    resetInactivityFlags();
    appendUserMessage(visibleText ?? textToSend);
    setInput("");
    clearPendingUi();
    setIsTyping(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend, session_id: sessionId }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const nextInputType  = data.input_type || null;
      const nextOptionsRaw = Array.isArray(data.options) ? data.options : [];
      const nextOptions    = nextOptionsRaw.map(normaliseOption);

      // Brief pause so typing indicator is visible before first bubble
      await wait(randDelay(120, 220));

      /** Append one text chunk as a bubble, converting plain text to rich HTML. */
      const appendBubble = (text) => {
        const isAlreadyHtml = containsHtml(text);
        const html          = isAlreadyHtml ? text : richTextToHtml(text);
        appendAssistantMessage(html, true);
      };

      if (Array.isArray(data.messages) && data.messages.length > 0) {
        for (let i = 0; i < data.messages.length; i++) {
          const msgText = String(data.messages[i]?.reply || "").trim();
          if (!msgText) continue;
          const isAlreadyHtml = containsHtml(msgText);
          const bubbles       = isAlreadyHtml ? [msgText] : splitIntoBubbles(msgText);
          for (let b = 0; b < bubbles.length; b++) {
            appendBubble(bubbles[b]);
            if (b < bubbles.length - 1 || i < data.messages.length - 1) {
              await wait(randDelay(180, 300));
            }
          }
        }
      } else {
        const replyText = String(data.reply || "No response returned.").trim();
        const isAlreadyHtml = containsHtml(replyText);
        const bubbles       = isAlreadyHtml ? [replyText] : splitIntoBubbles(replyText);
        for (let b = 0; b < bubbles.length; b++) {
          appendBubble(bubbles[b]);
          if (b < bubbles.length - 1) await wait(randDelay(180, 300));
        }
      }

      setPendingInputType(nextInputType);
      setPendingOptions(isSelectableInputType(nextInputType) ? nextOptions : []);

      const shouldStartInactivity =
        !isLikelyClosingMessage(textToSend) &&
        !isSelectableInputType(nextInputType) &&
        nextOptions.length === 0;

      shouldStartInactivity ? beginInactivityFlow() : clearInactivityTimers();
    } catch {
      await wait(150);
      appendAssistantMessage("Sorry, I could not connect to the server. Please try again.");
      clearPendingUi();
      clearInactivityTimers();
    } finally {
      setIsTyping(false);
    }
  };

  // ── Option / query handlers ─────────────────────────────────────────────────
  const handleSelectQuery  = (q)  => { setSelectedQuery(q); sendMessage(q); };
  const handleOptionSelect = (opt) => {
    const n = normaliseOption(opt);
    if (!n.value) return;
    sendMessage(n.value, n.label || n.value);
  };

  // ── Render helpers ──────────────────────────────────────────────────────────
  const getOptionHeading = () => {
    const count = pendingOptions.length;
    if (pendingInputType === "address_list")
      return `Select your property — ${count} found`;
    return `Please choose an option (${count} available)`;
  };

  const bandBadge = (band) => {
    const b = String(band || "").trim();
    if (!b) return null;
    return (
      <span className="inline-flex shrink-0 rounded-full border border-[#cfe0ff] bg-[#eef4ff] px-2.5 py-0.5 text-xs font-semibold text-[#123b7a]">
        {b.toLowerCase() === "deleted" ? "Deleted" : `Band ${b}`}
      </span>
    );
  };

  if (!chatOpen) return null;

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        onClick={() => setChatOpen(false)}
      />

      {/* Panel */}
      <div className="relative z-10 flex h-[96vh] w-full max-w-5xl flex-col overflow-hidden rounded-t-[1.5rem] border border-[#d6e0ef] bg-white shadow-2xl sm:h-[94vh] sm:rounded-[2rem]">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between gap-3 border-b border-[#d9e2f1] bg-gradient-to-r from-[#f0f6ff] to-white px-4 py-3 sm:gap-4 sm:px-6 sm:py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#0f4ca3] text-white shadow sm:h-11 sm:w-11 sm:rounded-2xl">
              <svg viewBox="0 0 24 24" className="h-4 w-4 sm:h-5 sm:w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="12" cy="8" r="3.2" />
                <path d="M5.5 19c1.4-3 4-4.5 6.5-4.5S17 16 18.5 19" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-[#123b7a] sm:text-xl">Bradford Council Assistant</h2>
                <span className="flex h-2 w-2 rounded-full bg-green-500 ring-2 ring-green-100" title="Online" />
              </div>
              <p className="hidden text-xs text-slate-500 sm:block">Live guidance &amp; service support</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={restartChat}
              className="rounded-xl border border-[#c9d7ee] bg-white px-3 py-1.5 text-xs font-medium text-[#123b7a] transition hover:bg-[#f0f6ff] sm:px-4 sm:py-2 sm:text-sm"
            >
              ↺ Restart
            </button>
            <button
              onClick={() => setChatOpen(false)}
              aria-label="Close chat"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-[#c9d7ee] bg-white text-[#123b7a] transition hover:bg-[#f0f6ff]"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* ── Messages area ───────────────────────────────────────────────── */}
        <div
          ref={scrollContainerRef}
          className="relative flex-1 overflow-y-auto bg-[#f5f7fb] px-3 py-4 sm:px-6 sm:py-6"
        >
          <div className="space-y-4 sm:space-y-5">
            {/* Intro messages */}
            {introMessages.map((msg, i) => (
              <div key={`intro-${i}`} className="fade-slide-in flex items-end gap-2 sm:gap-3">
                <AssistantAvatar />
                <div className="max-w-[85%] rounded-[1.25rem] rounded-tl-md bg-white px-4 py-3 shadow-sm sm:max-w-[72%] sm:px-5 sm:py-4">
                  <p className="text-sm font-semibold text-[#123b7a]">{msg.title}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{msg.text}</p>
                  <p className="mt-2 text-xs text-slate-400">{msg.time}</p>
                </div>
              </div>
            ))}

            {/* Quick-start chips */}
            {!selectedQuery && (
              <div className="fade-slide-in flex flex-wrap gap-2 pl-10 sm:pl-12">
                {starterQueries.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSelectQuery(q)}
                    className="rounded-full border border-[#b9cae6] bg-white px-3 py-1.5 text-xs font-medium text-[#123b7a] shadow-sm transition hover:bg-[#eef4ff] hover:border-[#0f4ca3] sm:px-4 sm:py-2 sm:text-sm"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            {/* Conversation messages */}
            {messages.map((msg, i) => (
              <div
                key={`${msg.role}-${i}`}
                className={`fade-slide-in flex items-end gap-2 sm:gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && <AssistantAvatar />}

                <div
                  className={`max-w-[88%] px-4 py-3 shadow-sm sm:max-w-[72%] sm:px-5 sm:py-4 ${
                    msg.role === "user"
                      ? "rounded-[1.25rem] rounded-tr-md bg-[#0f4ca3] text-white"
                      : "rounded-[1.25rem] rounded-tl-md bg-white text-slate-800"
                  }`}
                >
                  {msg.isHtml ? (
                    <div
                      className="break-words text-[15px] leading-7 [&_a]:font-semibold [&_a]:text-[#0f4ca3] [&_a]:underline [&_ul]:my-2 [&_ul]:space-y-1 [&_li]:leading-6 [&_strong]:font-semibold [&_table]:w-full [&_td]:py-1 [&_td]:pr-4"
                      dangerouslySetInnerHTML={{ __html: msg.text }}
                    />
                  ) : (
                    <p className="whitespace-pre-line break-words text-[15px] leading-7">{msg.text}</p>
                  )}
                  <p className={`mt-2 text-xs ${msg.role === "user" ? "text-blue-200" : "text-slate-400"}`}>
                    {msg.time}
                  </p>
                </div>

                {msg.role === "user" && <UserAvatar />}
              </div>
            ))}

            {/* Benefits calculator widget */}
            {pendingInputType === "calculator" && !isTyping && (
              <BenefitsCalculatorCard
                onResult={(summary) => { clearPendingUi(); sendMessage(summary); }}
              />
            )}

            {/* Feedback star widget */}
            {pendingInputType === "feedback" && !isTyping && (
              <FeedbackStars
                onRate={(rating) => { clearPendingUi(); sendMessage(rating); }}
              />
            )}

            {/* Option / address selector */}
            {isSelectableInputType(pendingInputType) && pendingOptions.length > 0 && !isTyping && (
              <div className="fade-slide-in flex items-start gap-2 sm:gap-3">
                <AssistantAvatar />
                <div className="w-full max-w-[88%] rounded-[1.25rem] rounded-tl-md bg-white px-3 py-3 shadow-sm sm:max-w-[72%] sm:px-4 sm:py-4">
                  <p className="mb-3 text-sm font-semibold text-[#123b7a]">{getOptionHeading()}</p>

                  <div
                    ref={addressBoxRef}
                    className="address-scrollbox max-h-72 overflow-y-auto rounded-2xl border border-[#d8e2f0] bg-[#f8fbff] p-2"
                  >
                    <div className="space-y-2">
                      {pendingOptions.map((opt, idx) => {
                        const n    = normaliseOption(opt);
                        const num  = n.display_index ?? idx + 1;
                        return (
                          <button
                            key={`${n.value || n.label}-${idx}`}
                            type="button"
                            onClick={() => handleOptionSelect(n)}
                            className="block w-full rounded-xl border border-[#d4deed] bg-white px-4 py-3 text-left transition hover:border-[#0f4ca3] hover:bg-[#eef4ff]"
                            title={n.label || n.value}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="flex min-w-0 items-center gap-3">
                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#eef4ff] text-xs font-bold text-[#0f4ca3]">
                                  {num}
                                </span>
                                <p className="break-words text-sm font-medium leading-6 text-slate-800">
                                  {n.label || n.value || "Select this option"}
                                </p>
                              </div>
                              {bandBadge(n.band)}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Typing indicator */}
            {isTyping && <TypingDots />}

            <div ref={messagesEndRef} />
          </div>

          {/* Scroll-to-bottom button */}
          {showScrollBtn && (
            <button
              onClick={scrollToBottom}
              className="absolute bottom-4 right-4 flex h-9 w-9 items-center justify-center rounded-full bg-white shadow-md border border-[#d6e0ef] text-[#0f4ca3] transition hover:bg-[#eef4ff]"
              aria-label="Scroll to bottom"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>

        {/* ── Input bar ───────────────────────────────────────────────────── */}
        <div className="border-t border-[#d7dfea] bg-white px-3 py-3 sm:px-5 sm:py-4">
          <div className="flex gap-2 sm:gap-3">
            <input
              value={input}
              onChange={(e) => { setInput(e.target.value); clearInactivityTimers(); }}
              onFocus={() => clearInactivityTimers()}
              onKeyDown={(e) => { if (e.key === "Enter" && !isTyping) sendMessage(); }}
              placeholder="Ask about bins, Council Tax…"
              className="flex-1 rounded-2xl border border-[#c8d5ea] bg-[#f8faff] px-4 py-3 text-[15px] text-slate-800 outline-none placeholder:text-slate-400 focus:border-[#0f4ca3] focus:bg-white transition sm:px-5 sm:py-3.5"
            />
            <button
              onClick={() => sendMessage()}
              disabled={isTyping || !input.trim()}
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#0f4ca3] text-white shadow transition hover:bg-[#0d438f] disabled:cursor-not-allowed disabled:opacity-50 sm:h-[52px] sm:w-[52px]"
              aria-label="Send message"
            >
              <SendIcon />
            </button>
          </div>
          <p className="mt-1.5 hidden text-center text-xs text-slate-400 sm:block">
            Press <kbd className="rounded border border-slate-200 bg-slate-100 px-1 py-0.5 text-[10px] font-mono">Enter</kbd> to send
          </p>
        </div>
      </div>
    </div>
  );
}
