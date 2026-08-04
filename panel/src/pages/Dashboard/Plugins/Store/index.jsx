import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { message, Spin } from "antd";
import {
  DownOutlined, SearchOutlined, DownloadOutlined,
  LikeOutlined, LikeFilled, GithubOutlined, CloudDownloadOutlined, CloseOutlined, ReloadOutlined,
  AppstoreOutlined,
} from "@ant-design/icons";
import PluginPagination from "../../../../components/PluginPagination";
import { matchPlugin } from "../../../../utils/pluginSearch";

const CATEGORIES = ["Entertainment", "Tools", "Manage", "Media", "Ai", "News", "Life", "Dev", "Other"];
const PAGE_SIZE = 12;

export default function PluginStore() {
  const { t, i18n } = useTranslation();
  const [plugins, setPlugins] = useState(null);
  const [sources, setSources] = useState([]);
  const [source, setSource] = useState("");
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("default");
  const [page, setPage] = useState(1);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [sortOpen, setSortOpen] = useState(false);
  const [catOpen, setCatOpen] = useState(false);
  const [busy, setBusy] = useState("");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    setIsMobile(mq.matches);
    const fn = (e) => setIsMobile(e.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  const [refreshing, setRefreshing] = useState(false);

  const load = async (force = false) => {
    try {
      const res = await fetch(`/api/loyanui/store/plugins${force ? "?force=1" : ""}`).then((r) => r.json());
      if (res.success) setPlugins(res.data || []);
    } catch {
      setPlugins([]);
    }
    try {
      const cfg = await fetch("/api/loyanui/store/config").then((r) => r.json());
      const srcs = (cfg.data?.sources || []).filter((s) => s.enabled);
      setSources(srcs);
      setSource((prev) => prev || srcs[0]?.name || "");
    } catch { /* ignore */ }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!plugins) return [];
    let list = plugins.filter((p) => !source || p.source === source);
    if (category) list = list.filter((p) => p.category === category);
    if (keyword.trim()) {
      list = list.filter((p) => matchPlugin(p, keyword));
    }
    const cmp = {
      default: (a, b) => 0,
      updated: (a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")),
      downloads: (a, b) => (b.downloads || 0) - (a.downloads || 0),
      author: (a, b) => String(a.author || "").localeCompare(String(b.author || "")),
      likes: (a, b) => (b.likes || 0) - (a.likes || 0),
    }[sort] || cmp.default;
    return [...list].sort(cmp);
  }, [plugins, source, category, keyword, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const pagePlugins = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  const doLike = async (p) => {
    if (p.liked) {
      message.info(t("plugins.alreadyLiked"), 2);
      return;
    }
    if (busy === p.id) return;
    setBusy(p.id);
    try {
      const res = await fetch(`/api/loyanui/store/plugins/${p.id}/like`, { method: "POST" }).then((r) => r.json());
      if (res.success) {
        setPlugins((prev) =>
          prev.map((x) => (x.id === p.id ? { ...x, likes: (x.likes || 0) + 1, liked: true } : x))
        );
      }
    } catch { /* ignore */ }
    setBusy("");
  };

  const doInstall = async (p) => {
    if (busy === p.id) return;
    setBusy(p.id);
    try {
      const res = await fetch(`/api/loyanui/store/plugins/${p.id}/install`, { method: "POST" }).then((r) => r.json());
      if (res.success) {
        message.success(t("plugins.installSuccess"));
        load();
      } else {
        message.error(res.message || t("plugins.installFailed"));
      }
    } catch {
      message.error(t("plugins.installFailed"));
    }
    setBusy("");
  };

  const pickerStyle = {
    display: "flex", alignItems: "center", gap: 6,
    padding: "6px 12px", borderRadius: 999,
    border: "1px solid var(--primary)", background: "var(--card-bg)",
    color: "var(--primary)", cursor: "pointer", fontSize: 13, whiteSpace: "nowrap",
  };

  const searchBox = (
    <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 999, border: "1px solid var(--sidebar-border)", background: "var(--card-bg)" }}>
      <SearchOutlined style={{ color: "var(--text-secondary)" }} />
      <input
        value={keyword}
        onChange={(e) => { setKeyword(e.target.value); setPage(1); }}
        placeholder={isMobile ? t("plugins.searchPlaceholderShort") : t("plugins.searchPlaceholder")}
        style={{ flex: 1, minWidth: 0, border: "none", outline: "none", background: "transparent", color: "var(--text)", fontSize: 14 }}
      />
      {keyword && (
        <CloseOutlined
          onClick={() => { setKeyword(""); setPage(1); }}
          style={{ color: "var(--text-secondary)", cursor: "pointer", fontSize: 12, flexShrink: 0 }}
        />
      )}
    </div>
  );

  return (
    <div>
      <div className="store-fixed-bar">
        <div className="store-title-row">
          <h2 style={{ color: "var(--text)", fontSize: 18, margin: 0, whiteSpace: "nowrap" }}>{t("plugins.storeTitle")}</h2>
        </div>
        <div className="store-search-mobile" style={{ marginBottom: 8 }}>{searchBox}</div>

        <div className="store-toolbar" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", margin: "0 0 8px" }}>
        <button
          onClick={async () => { setRefreshing(true); await load(true); setRefreshing(false); }}
          disabled={refreshing}
          title={t("plugins.refresh")}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 30, height: 30, borderRadius: 999, cursor: "pointer",
            border: "1px solid var(--primary)", background: "var(--card-bg)",
            color: "var(--primary)", fontSize: 14, flexShrink: 0,
          }}
        >
          {refreshing ? <Spin size="small" /> : <ReloadOutlined />}
        </button>
        <div style={{ position: "relative" }}>
          <div style={pickerStyle} onClick={() => setSourceOpen(!sourceOpen)}>
            <AppstoreOutlined />
            <span>{source || t("plugins.officialSource")}</span>
            <DownOutlined style={{ fontSize: 10 }} />
          </div>
          {sourceOpen && (
            <div style={{
              position: "absolute", top: "100%", left: 0, marginTop: 4, zIndex: 20,
              background: "var(--card-bg)", border: "1px solid var(--sidebar-border)",
              borderRadius: 8, padding: 4, minWidth: 140, boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
            }}>
              {sources.length === 0 && (
                <div style={{ padding: "6px 12px", color: "var(--text-secondary)", fontSize: 13 }}>{t("plugins.officialSource")}</div>
              )}
              {sources.map((s) => (
                <div
                  key={s.name}
                  onClick={() => { setSource(s.name); setPage(1); setSourceOpen(false); }}
                  style={{
                    padding: "6px 12px", borderRadius: 6, cursor: "pointer", fontSize: 13,
                    color: s.name === source ? "var(--primary)" : "var(--text)",
                    background: s.name === source ? "var(--bg-mid)" : "transparent",
                  }}
                >
                  {s.name}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="store-search-desktop" style={{ flex: 1, minWidth: 200 }}>{searchBox}</div>

        <div style={{ position: "relative" }}>
          <div style={pickerStyle} onClick={() => setSortOpen(!sortOpen)}>
            <span>{t(`plugins.sort${sort[0].toUpperCase()}${sort.slice(1)}`)}</span>
            <DownOutlined style={{ fontSize: 10 }} />
          </div>
          {sortOpen && (
            <div style={{
              position: "absolute", top: "100%", right: 0, marginTop: 4, zIndex: 20,
              background: "var(--card-bg)", border: "1px solid var(--sidebar-border)",
              borderRadius: 8, padding: 4, minWidth: 140, boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
            }}>
              {["default", "updated", "downloads", "author", "likes"].map((s) => (
                <div
                  key={s}
                  onClick={() => { setSort(s); setPage(1); setSortOpen(false); }}
                  style={{
                    padding: "6px 12px", borderRadius: 6, cursor: "pointer", fontSize: 13,
                    color: s === sort ? "var(--primary)" : "var(--text)",
                    background: s === sort ? "var(--bg-mid)" : "transparent",
                  }}
                >
                  {t(`plugins.sort${s[0].toUpperCase()}${s.slice(1)}`)}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="store-cat-mobile" style={{ position: "relative" }}>
          <div style={pickerStyle} onClick={() => setCatOpen(!catOpen)}>
            <span>{category ? t(`plugins.category${category}`) : t("plugins.all")}</span>
            <DownOutlined style={{ fontSize: 10 }} />
          </div>
          {catOpen && (
            <div style={{
              position: "absolute", top: "100%", right: 0, marginTop: 4, zIndex: 20,
              background: "var(--card-bg)", border: "1px solid var(--sidebar-border)",
              borderRadius: 8, padding: 4, minWidth: 140, boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
            }}>
              {["", ...CATEGORIES].map((cc) => (
                <div
                  key={cc || "all"}
                  onClick={() => { setCategory(cc); setPage(1); setCatOpen(false); }}
                  style={{
                    padding: "6px 12px", borderRadius: 6, cursor: "pointer", fontSize: 13,
                    color: cc === category ? "var(--primary)" : "var(--text)",
                    background: cc === category ? "var(--bg-mid)" : "transparent",
                  }}
                >
                  {cc ? t(`plugins.category${cc}`) : t("plugins.all")}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      </div>

      <div className="plugin-store-body">
        <div className="plugin-cats">
          {["", ...CATEGORIES].map((c) => (
            <button
              key={c || "all"}
              onClick={() => { setCategory(c); setPage(1); }}
              style={{
                padding: "5px 14px", borderRadius: 999, cursor: "pointer", fontSize: 13, whiteSpace: "nowrap",
                border: c === category ? "1px solid var(--primary)" : "1px solid var(--sidebar-border)",
                background: c === category ? "var(--primary)" : "var(--card-bg)",
                color: c === category ? "#fff" : "var(--text)",
              }}
            >
              {c ? t(`plugins.category${c}`) : t("plugins.all")}
            </button>
          ))}
        </div>

        <div className="plugin-grid">
          {!plugins && (
            <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "center", padding: 60 }}>
              <Spin size="large" />
            </div>
          )}
          {plugins && pagePlugins.length === 0 && (
            <div style={{ gridColumn: "1 / -1", textAlign: "center", color: "var(--text-secondary)", padding: 40 }}>
              {t("plugins.noPlugins")}
            </div>
          )}
          {plugins && pagePlugins.map((p) => (
            <div key={p.id} className="plugin-card" style={{ background: "var(--card-bg)", border: "1px solid var(--sidebar-border)" }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                {p.icon ? (
                  <img src={p.icon} alt="" referrerPolicy="no-referrer" style={{ width: 48, height: 48, borderRadius: 10, objectFit: "cover", flexShrink: 0 }} />
                ) : (
                  <div style={{
                    width: 48, height: 48, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
                    background: "var(--primary)", color: "#fff", fontSize: 24, flexShrink: 0,
                  }}>
                    {(p.name || "P").slice(0, 1)}
                  </div>
                )}
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ color: "var(--text)", fontWeight: 600, fontSize: 15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.name}>
                    {p.name}
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: 12, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", lineHeight: "1.5", minHeight: 36, marginTop: 2 }} title={p.description}>
                    {p.description}
                  </div>
                </div>
              </div>
              <div className="plugin-actions">
                <div className="pa-left">
                  <button
                    onClick={() => doLike(p)}
                    style={{ display: "flex", alignItems: "center", gap: 4, border: "none", background: "transparent", cursor: "pointer", color: "var(--primary)", fontSize: 13 }}
                    title={p.liked ? t("plugins.liked") : t("plugins.like")}
                  >
                    {p.liked ? <LikeFilled style={{ color: "var(--primary)" }} /> : <LikeOutlined />}
                    <span>{p.likes ?? 0}</span>
                  </button>
                  <span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--text-secondary)", fontSize: 13, lineHeight: 1 }}>
                    <DownloadOutlined />
                    <span>{p.downloads ?? 0}</span>
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 4, minWidth: 0, color: "var(--text-secondary)", fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.author}>
                    {t("plugins.authorLabel")} {p.author}
                  </span>
                  <span style={{ color: "var(--primary)", fontWeight: 600, fontSize: 12, alignSelf: "center" }}>v{p.version}</span>
                </div>
                <div className="pa-right">
                  <a
                    href={p.docs_url || (p.repo ? `https://github.com/${p.repo}` : "#")}
                    target="_blank" rel="noreferrer"
                    style={{ color: "var(--text-secondary)", fontSize: 16, lineHeight: 1, marginRight: 8 }}
                    title={t("plugins.github")}
                  >
                    <GithubOutlined />
                  </a>
                  <button
                    onClick={() => doInstall(p)}
                    disabled={busy === p.id}
                    style={{
                      padding: "3px 12px", borderRadius: 999, cursor: p.installed ? "default" : "pointer", fontSize: 12,
                      border: "1px solid var(--primary)",
                      background: p.installed ? "transparent" : "var(--primary)",
                      color: p.installed ? "var(--primary)" : "#fff",
                    }}
                  >
                    {p.installed ? (p.update_available ? t("plugins.update") : t("plugins.installed")) : t("plugins.install")}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <PluginPagination current={current} total={pageCount} onChange={setPage} />
    </div>
  );
}
