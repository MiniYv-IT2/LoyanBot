import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Drawer, Select, Switch, message } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import tsx from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import jsx from "react-syntax-highlighter/dist/esm/languages/prism/jsx";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import css from "react-syntax-highlighter/dist/esm/languages/prism/css";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import java from "react-syntax-highlighter/dist/esm/languages/prism/java";
import c from "react-syntax-highlighter/dist/esm/languages/prism/c";
import cpp from "react-syntax-highlighter/dist/esm/languages/prism/cpp";
import go from "react-syntax-highlighter/dist/esm/languages/prism/go";
import rust from "react-syntax-highlighter/dist/esm/languages/prism/rust";
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import yaml from "react-syntax-highlighter/dist/esm/languages/prism/yaml";

SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("javascript", javascript);
SyntaxHighlighter.registerLanguage("typescript", typescript);
SyntaxHighlighter.registerLanguage("tsx", tsx);
SyntaxHighlighter.registerLanguage("jsx", jsx);
SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("json", json);
SyntaxHighlighter.registerLanguage("css", css);
SyntaxHighlighter.registerLanguage("sql", sql);
SyntaxHighlighter.registerLanguage("java", java);
SyntaxHighlighter.registerLanguage("c", c);
SyntaxHighlighter.registerLanguage("cpp", cpp);
SyntaxHighlighter.registerLanguage("go", go);
SyntaxHighlighter.registerLanguage("rust", rust);
SyntaxHighlighter.registerLanguage("markdown", markdown);
SyntaxHighlighter.registerLanguage("yaml", yaml);
SyntaxHighlighter.registerLanguage("txt", markdown);
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DeleteOutlined,
  MessageOutlined,
  PlusOutlined,
  RobotOutlined,
  UserOutlined,
  CopyOutlined,
  CheckOutlined,
} from "@ant-design/icons";
import {
  Bubble,
  Conversations,
  Prompts,
  Sender,
  Think,
  Welcome,
  XProvider,
} from "@ant-design/x";
import "../../../styles/chat.css";

let uid = 0;
const nextKey = () => `m${Date.now().toString(36)}_${uid++}`;

const DEFAULT_PERSONA = "__default__";

function compactBlankLines(md) {
  const parts = String(md || "").split(/(```[\s\S]*?```)/g);
  return parts.map((p, i) => (i % 2 === 1 ? p : p.replace(/\n{3,}/g, "\n\n"))).join("");
}

function ThinkSvg({ size = 14 }) {
  return (
    <svg viewBox="0 0 1024 1024" fill="currentColor" width={size} height={size} role="img" aria-label="think">
      <path d="M847.936 168.448c65.088 65.664 46.144 198.528-36.224 337.536 88.128 143.04 109.824 281.408 43.008 348.8-66.56 67.072-202.688 45.696-343.808-41.984-141.12 87.68-277.248 109.056-343.808 41.984-66.816-67.392-45.056-205.76 43.008-348.8-82.368-139.008-101.248-271.872-36.16-337.536 65.408-65.92 198.336-46.336 336.96 37.76l9.728-5.76c135.104-79.232 263.36-96.448 327.296-32zM249.088 565.568l-2.24 4.16a536.704 536.704 0 0 0-38.272 85.696c-28.928 85.888-16.128 134.144 3.584 153.984 19.712 19.776 67.52 32.768 152.704 3.584a531.84 531.84 0 0 0 87.616-40.064c-35.84-26.816-71.488-57.664-105.792-92.288a950.4 950.4 0 0 1-97.6-115.072z m523.648 0.064l-2.56 3.584c-27.392 37.76-59.2 75.328-94.976 111.424a951.744 951.744 0 0 1-105.856 92.288c30.336 17.088 59.904 30.528 87.68 40.064 85.12 29.184 132.992 16.192 152.64-3.584 19.712-19.84 32.576-68.096 3.584-153.984a541.824 541.824 0 0 0-40.512-89.792z m-261.76-283.2l-17.664 12.416c-36.352 26.24-72.96 57.472-108.416 93.184a878.208 878.208 0 0 0-99.008 118.656c28.8 42.88 64.128 86.528 105.792 128.512a874.24 874.24 0 0 0 119.232 100.928 875.84 875.84 0 0 0 119.232-100.928 871.232 871.232 0 0 0 105.728-128.448 868.224 868.224 0 0 0-98.944-118.72 867.136 867.136 0 0 0-126.016-105.6z m3.2 105.472a11.52 11.52 0 0 1 7.808 7.808l7.232 24.512c10.432 35.2 37.888 62.72 73.088 73.152l24.192 7.168a11.52 11.52 0 0 1 0.064 22.144l-24.704 7.424A108.288 108.288 0 0 0 529.28 603.008l-7.296 24.576a11.52 11.52 0 0 1-22.144 0l-7.296-24.576a108.288 108.288 0 0 0-72.576-72.96l-24.704-7.36a11.52 11.52 0 0 1 0-22.144l24.32-7.168c35.136-10.432 62.592-37.952 73.024-73.152l7.232-24.512a11.52 11.52 0 0 1 14.336-7.808z m136.064-177.664a522.496 522.496 0 0 0-79.872 35.776c37.76 27.84 75.456 60.16 111.552 96.64a956.16 956.16 0 0 1 89.856 104.32c14.656-27.392 26.24-54.016 34.688-79.168 28.928-85.888 16.064-134.08-3.52-153.984-19.712-19.776-67.52-32.768-152.704-3.584z m-431.36 3.584c-19.584 19.84-32.512 68.096-3.52 153.984 8.512 25.152 20.096 51.776 34.688 79.168 26.24-35.392 56.32-70.528 89.856-104.32a948.224 948.224 0 0 1 111.616-96.64 514.816 514.816 0 0 0-79.936-35.776c-85.12-29.184-132.928-16.192-152.64 3.584z" />
    </svg>
  );
}

function CopyFullButton({ text }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };
  return (
    <button type="button" className="chat-msg-copy" onClick={onCopy}>
      {copied ? <CheckOutlined style={{ color: "#52c41a" }} /> : <CopyOutlined />}
    </button>
  );
}

const CodeBlock = memo(function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="chat-code-block">
      <div className="chat-code-bar">
        <span className="chat-code-lang">{language}</span>
        <button type="button" className="chat-code-copy" onClick={onCopy} title="复制代码">
          {copied ? <CheckOutlined style={{ color: "#52c41a" }} /> : <CopyOutlined />}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{ margin: 0, borderRadius: "0 0 8px 8px", fontSize: 13 }}
        codeTagProps={{ style: { fontSize: 13, lineHeight: 1.6 } }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
});

const Markdown = memo(function Markdown({ source }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkBreaks]}
      rehypePlugins={[rehypeRaw, rehypeSanitize]}
      components={{
        code({ inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const text = String(children).replace(/\n$/, "");
          if (!inline) {
            if (!text.includes("\n") && !match) {
              return <code className="chat-inline-code chat-inline-block" {...props}>{children}</code>;
            }
            return <CodeBlock language={match ? match[1] : "text"} code={text} />;
          }
          return <code className="chat-inline-code" {...props}>{children}</code>;
        },
        table({ children, ...props }) {
          return (
            <div className="chat-table-wrap">
              <table {...props}>{children}</table>
            </div>
          );
        },
      }}
    >
      {compactBlankLines(source)}
    </ReactMarkdown>
  );
});

const MessageBody = memo(function MessageBody({ m, isStreaming, t }) {
  const data = m;
  return (
    <div className="chat-bubble-body">
      {data?.reasoning ? (
        <Think
          title={t("chat.thinking")}
          loading={isStreaming}
          blink={isStreaming}
          defaultExpanded={false}
          classNames={{ root: "chat-think", content: "chat-think-content" }}
        >
          <div className="chat-think-md"><Markdown source={data.reasoning} /></div>
        </Think>
      ) : null}
      <div className="chat-bubble-text">
        {data?.content ? (
          <Markdown source={data.content} />
        ) : null}
        {isStreaming ? <span className="chat-cursor" /> : null}
      </div>
      {!isStreaming && data?.content ? (
        <div className="chat-msg-actions">
          <CopyFullButton text={data.content} />
          {data.duration > 0 ? (
            <span className="chat-msg-time">
              {data.duration >= 60
                ? t("chat.durationMinSec", {
                    min: Math.floor(data.duration / 60),
                    sec: Math.round(data.duration % 60),
                  })
                : t("chat.durationSec", { sec: Math.round(data.duration) })}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});

export default function ChatPage() {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [providers, setProviders] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [instanceId, setInstanceId] = useState("");
  const [persona, setPersona] = useState("");
  const [showThinking, setShowThinking] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef(null);
  const taskIdRef = useRef(null);
  const streamingRef = useRef(false);

  // 初始加载：会话列表 + 提供商 + 人设
  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [sRes, pRes, peRes] = await Promise.all([
          fetch("/api/loyanui/chat/sessions").then((r) => r.json()),
          fetch("/api/loyanui/providers").then((r) => r.json()),
          fetch("/api/loyanui/chat/personas").then((r) => r.json()),
        ]);
        if (cancel) return;
        const list = sRes?.success ? sRes.data || [] : [];
        setSessions(list);
        const ps = Array.isArray(pRes?.data) ? pRes.data : [];
        setProviders(ps);
        const first = ps.find((p) => p.enabled) || ps[0];
        if (first) setInstanceId(first.id);
        setPersonas(Array.isArray(peRes?.data) ? peRes.data : []);
        if (list.length > 0) setActiveId(list[0].id);
      } catch {
        if (!cancel) message.error(t("chat.loadFailed"));
      }
    })();
    return () => { cancel = true; };
  }, []);

  // 卸载时中止在途请求
  useEffect(() => () => abortRef.current?.abort(), []);

  const appendMessage = useCallback((role, content) => {
    const id = nextKey();
    setMessages((prev) => [...prev, { id, role, content, reasoning: "", duration: 0 }]);
    return id;
  }, []);

  const patchMessage = useCallback((id, updater) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? updater(m) : m)));
  }, []);

  // 订阅任务事件流，增量渲染到指定消息；返回是否收到 close 完成
  const consumeTaskStream = useCallback(async (taskId, aiId, controller) => {
    const res = await fetch(`/api/loyanui/chat/tasks/${taskId}/events`, { signal: controller.signal });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let pendReasoning = "";
    let pendContent = "";
    let flushTimer = null;
    const flushPend = () => {
      flushTimer = null;
      if (!pendReasoning && !pendContent) return;
      const r = pendReasoning;
      const c = pendContent;
      pendReasoning = "";
      pendContent = "";
      patchMessage(aiId, (m) => ({ ...m, reasoning: (m.reasoning || "") + r, content: (m.content || "") + c }));
    };
    const scheduleFlush = () => {
      if (!flushTimer) flushTimer = setTimeout(flushPend, 60);
    };
    let finished = false;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = chunk.trim();
        if (!line.startsWith("data:")) continue;
        let evt;
        try { evt = JSON.parse(line.slice(5).trim()); } catch { continue; }
        if (evt?.type === "reasoning" && evt.content) {
          pendReasoning += evt.content;
          scheduleFlush();
        } else if (evt?.type === "text" && evt.content) {
          pendContent += evt.content;
          scheduleFlush();
        } else if (evt?.type === "close") {
          finished = true;
          flushPend();
          break;
        } else if (evt?.type === "done") {
          const dur = typeof evt.elapsed === "number" ? evt.elapsed : typeof evt.time === "number" ? evt.time : 0;
          if (dur > 0) {
            patchMessage(aiId, (m) => ({ ...m, duration: dur }));
          }
        }
      }
      if (finished) break;
    }
    flushPend();
    return finished;
  }, [patchMessage]);

  // 切换会话时加载历史消息；若该会话有运行中任务则续收流
  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    let cancel = false;
    setMessages([]);
    fetch(`/api/loyanui/chat/sessions/${activeId}/messages`)
      .then((r) => r.json())
      .then((res) => {
        if (cancel || streamingRef.current) return;
        const data = Array.isArray(res?.data) ? res.data : [];
        const list = data.map((m) => ({
          id: nextKey(),
          role: m.role === "user" ? "user" : "assistant",
          content: m.content || "",
          reasoning: m.reasoning || "",
          duration: m.duration || 0,
        }));
        setMessages(list);
        fetch("/api/loyanui/chat/tasks")
          .then((r) => r.json())
          .then((tRes) => {
            if (cancel) return;
            const tasks = Array.isArray(tRes?.data) ? tRes.data : [];
            const active = tasks.find((t) => t.session_id === activeId && t.status === "running");
            if (!active) return;
            const aiId = nextKey();
            setMessages((prev) => [...prev, { id: aiId, role: "assistant", content: "", reasoning: "", duration: 0 }]);
            setStreaming(true);
            streamingRef.current = true;
            const controller = new AbortController();
            abortRef.current = controller;
            taskIdRef.current = active.task_id;
            consumeTaskStream(active.task_id, aiId, controller)
              .then(() => {
                taskIdRef.current = null;
                setStreaming(false);
                streamingRef.current = false;
              })
              .catch(() => {
                taskIdRef.current = null;
                setStreaming(false);
                streamingRef.current = false;
              });
          })
          .catch(() => {});
      })
      .catch(() => { if (!cancel) message.error(t("chat.loadFailed")); });
    return () => { cancel = true; };
  }, [activeId, consumeTaskStream, t]);

  const createSession = useCallback(async (name) => {
    try {
      const res = await fetch("/api/loyanui/chat/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || t("chat.newChat") }),
      }).then((r) => r.json());
      if (!res?.success || !res.data) throw new Error("create failed");
      setSessions((prev) => [
        { id: res.data.id, name: res.data.name, created: Date.now() },
        ...prev,
      ]);
      return res.data.id;
    } catch {
      message.error(t("chat.createFailed"));
      return null;
    }
  }, [t]);

  const newChat = useCallback(() => {
    createSession().then((id) => {
      if (!id) return;
      abortRef.current?.abort();
      setStreaming(false);
      streamingRef.current = false;
      setActiveId(id);
      setMessages([]);
    });
  }, [createSession]);

  const removeSession = useCallback((sid) => {
    fetch(`/api/loyanui/chat/sessions/${sid}`, { method: "DELETE" })
      .then((r) => r.json())
      .then((res) => {
        if (!res?.success) throw new Error("delete failed");
        if (activeId === sid) abortRef.current?.abort();
        setSessions((prev) => prev.filter((s) => s.id !== sid));
        if (activeId === sid) {
          setStreaming(false);
          streamingRef.current = false;
          setActiveId(null);
          setMessages([]);
        }
      })
      .catch(() => message.error(t("chat.deleteFailed")));
  }, [activeId, t]);

  const switchSession = useCallback((key) => {
    if (key === activeId) return;
    abortRef.current?.abort();
    setStreaming(false);
    streamingRef.current = false;
    setActiveId(key);
  }, [activeId]);

  const send = useCallback(async (raw) => {
    const text = (raw || "").trim();
    if (!text || streaming) return;
    let sid = activeId;
    if (!sid) {
      sid = await createSession(text.slice(0, 20));
      if (!sid) return;
    }
    appendMessage("user", text);
    const aiId = appendMessage("assistant", "");
    setInput("");
    setStreaming(true);
    streamingRef.current = true;
    const controller = new AbortController();
    abortRef.current = controller;
    let finished = false;
    let taskId = null;
    try {
      const taskRes = await fetch("/api/loyanui/chat/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: sid,
          instance_id: instanceId || "",
          persona: persona || "",
          strip_think: !showThinking,
        }),
      });
      if (!taskRes.ok) throw new Error(`HTTP ${taskRes.status}`);
      const taskData = await taskRes.json();
      if (!taskData?.success || !taskData?.data?.task_id) throw new Error("task_create_failed");
      taskId = taskData.data.task_id;
      taskIdRef.current = taskId;
      finished = await consumeTaskStream(taskId, aiId, controller);
    } catch (e) {
      if (e?.name !== "AbortError") message.error(t("chat.sendFailed"));
    } finally {
      taskIdRef.current = null;
      setStreaming(false);
      streamingRef.current = false;
      if (abortRef.current === controller) abortRef.current = null;
      if (finished) {
        fetch("/api/loyanui/chat/sessions")
          .then((r) => r.json())
          .then((res) => { if (res?.success) setSessions(res.data || []); })
          .catch(() => {});
      }
    }
  }, [activeId, streaming, instanceId, persona, showThinking, appendMessage, createSession, consumeTaskStream, t]);

  const items = useMemo(
    () => messages.map((m) => ({ key: m.id, role: m.role, content: m.content, reasoning: m.reasoning })),
    [messages]
  );
  const lastStreamingId = streaming ? messages[messages.length - 1]?.id : null;

  const assistantRender = (content, info) => {
    const data = info?.key != null ? messages.find((m) => m.id === info.key) : null;
    const isStreaming = lastStreamingId != null && info?.key === lastStreamingId;
    if (!data) return null;
    return <MessageBody m={data} isStreaming={isStreaming} t={t} />;
  };

  const roles = {
    assistant: {
      placement: "start",
      avatar: <RobotOutlined className="chat-avatar-icon" />,
      styles: { content: { background: "transparent", color: "var(--text)", padding: 0 } },
      contentRender: assistantRender,
    },
    user: {
      placement: "end",
      avatar: <UserOutlined className="chat-avatar-icon" />,
      styles: { content: { background: "var(--primary)", color: "#fff" } },
    },
  };

  const convItems = sessions.map((s) => ({ key: s.id, label: s.name }));

  return (
    <XProvider>
      <div className="chat-page">

        {sidebarOpen ? (
          <aside className="chat-side">
            <div className="chat-convs">
              <Conversations
                items={convItems}
                activeKey={activeId}
                onActiveChange={switchSession}
                creation={{ icon: <PlusOutlined />, label: t("chat.newChat"), onClick: newChat }}
                menu={(item) => ({
                  items: [
                    {
                      key: "delete",
                      danger: true,
                      icon: <DeleteOutlined />,
                      label: t("chat.delete"),
                      onClick: () => removeSession(item.key),
                    },
                  ],
                })}
              />
            </div>
          </aside>
        ) : null}

        <Drawer
          placement="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          width={260}
          styles={{
            wrapper: { top: 56, height: "calc(100% - 56px)" },
            mask: { top: 56 },
            body: { padding: 12, background: "var(--card-bg)" },
          }}
        >
          <div className="chat-convs" style={{ height: "100%" }}>
            <Conversations
              items={convItems}
              activeKey={activeId}
              onActiveChange={(k) => { switchSession(k); setDrawerOpen(false); }}
              creation={{ icon: <PlusOutlined />, label: t("chat.newChat"), onClick: () => { newChat(); setDrawerOpen(false); } }}
              menu={(item) => ({
                items: [{
                  key: "delete", danger: true, icon: <DeleteOutlined />,
                  label: t("chat.delete"),
                  onClick: () => removeSession(item.key),
                }],
              })}
            />
          </div>
        </Drawer>

        <main className="chat-main">
          {/* 会话边栏开关：桌面展开/收起侧栏，手机开/关抽屉 */}
          <button
            className="chat-side-toggle"
            onClick={() => {
              if (window.innerWidth <= 768) setDrawerOpen((v) => !v);
              else setSidebarOpen((v) => !v);
            }}
            aria-label={t("chat.chatTitle")}
          >
            {window.innerWidth <= 768 ? (
              drawerOpen ? (
                <MenuFoldOutlined style={{ fontSize: 18 }} />
              ) : (
                <MenuUnfoldOutlined style={{ fontSize: 18 }} />
              )
            ) : sidebarOpen ? (
              <MenuFoldOutlined style={{ fontSize: 18 }} />
            ) : (
              <MenuUnfoldOutlined style={{ fontSize: 18 }} />
            )}
          </button>
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <Welcome
                icon={<RobotOutlined />}
                title={t("chat.welcomeTitle")}
                description={t("chat.welcomeDesc")}
                classNames={{
                  root: "chat-welcome-card",
                  title: "chat-welcome-title",
                  description: "chat-welcome-desc",
                }}
              />
              <Prompts
                wrap
                vertical
                title={activeId ? t("chat.emptyHistory") : null}
                items={[
                  { key: "p1", label: t("chat.prompt1"), icon: <MessageOutlined /> },
                  { key: "p2", label: t("chat.prompt2"), icon: <MessageOutlined /> },
                  { key: "p3", label: t("chat.prompt3"), icon: <MessageOutlined /> },
                ]}
                onItemClick={({ data }) => setInput(data.label)}
                classNames={{
                  root: "chat-prompts",
                  title: "chat-prompts-title",
                  item: "chat-prompt-item",
                  itemContent: "chat-prompt-content",
                }}
              />
            </div>
          ) : (
            <div className="chat-list">
              <Bubble.List items={items} autoScroll role={roles} />
            </div>
          )}

          <div className="chat-sender-wrap">
            <div className="chat-ctl-corner">
              <button
                type="button"
                className={`chat-think-toggle${showThinking ? " on" : ""}`}
                onClick={() => setShowThinking((v) => !v)}
                title={t("chat.showThinking")}
              >
                <ThinkSvg size={14} />
                <span>{t("chat.showThinking")}</span>
              </button>
              <Select
                className="chat-ctl-select"
                size="small"
                placeholder={t("chat.model")}
                value={instanceId || undefined}
                onChange={setInstanceId}
                options={providers.map((p) => ({
                  value: p.id,
                  label: `${p.id} · ${p.model}`,
                  disabled: !p.enabled,
                }))}
                popupMatchSelectWidth={false}
              />
              <Select
                className="chat-ctl-select"
                size="small"
                placeholder={t("chat.persona")}
                value={persona || DEFAULT_PERSONA}
                onChange={(v) => setPersona(v === DEFAULT_PERSONA ? "" : v)}
                options={[
                  { value: DEFAULT_PERSONA, label: t("chat.personaDefault") },
                  ...personas.map((p) => ({ value: p.name, label: p.name })),
                ]}
                popupMatchSelectWidth={false}
              />
            </div>
            <Sender
              value={input}
              onChange={setInput}
              onSubmit={(msg) => send(msg)}
              loading={streaming}
              onCancel={() => {
                const tid = taskIdRef.current;
                if (tid) fetch(`/api/loyanui/chat/tasks/${tid}/cancel`, { method: "POST" }).catch(() => {});
                abortRef.current?.abort();
              }}
              placeholder={t("chat.inputPlaceholder")}
              disabled={!instanceId}
              autoSize={{ minRows: 2, maxRows: 6 }}
              styles={{
                root: {
                  background: "var(--card-bg)",
                  border: "1px solid var(--sidebar-border)",
                  borderRadius: 12,
                },
                input: { color: "var(--text)", paddingLeft: 150 },
              }}
              classNames={{ input: "chat-sender-input" }}
            />
          </div>
        </main>
      </div>
    </XProvider>
  );
}
