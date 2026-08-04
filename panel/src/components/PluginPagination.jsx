import { LeftOutlined, RightOutlined } from "@ant-design/icons";

function pageList(current, total) {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages = new Set([1, total, current - 1, current, current + 1]);
  const list = [];
  let prev = 0;
  for (let p of [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b)) {
    if (p - prev > 1) list.push("...");
    list.push(p);
    prev = p;
  }
  return list;
}

export default function PluginPagination({ current, total, onChange }) {
  const items = pageList(current, total);
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "16px 0" }}>
      <button
        onClick={() => current > 1 && onChange(current - 1)}
        disabled={current <= 1}
        style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          width: 32, height: 32, borderRadius: 6, cursor: current > 1 ? "pointer" : "not-allowed",
          border: "1px solid var(--sidebar-border)", background: "var(--card-bg)",
          color: current > 1 ? "var(--primary)" : "var(--text-secondary)",
        }}
        aria-label="previous"
      >
        <LeftOutlined />
      </button>
      {items.map((p, i) =>
        p === "..." ? (
          <span key={`e${i}`} style={{ color: "var(--text-secondary)", padding: "0 4px" }}>…</span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p)}
            style={{
              minWidth: 32, height: 32, padding: "0 8px", borderRadius: 6, cursor: "pointer",
              border: p === current ? "1px solid var(--primary)" : "1px solid var(--sidebar-border)",
              background: p === current ? "var(--primary)" : "var(--card-bg)",
              color: p === current ? "#fff" : "var(--text)",
              fontWeight: p === current ? 600 : 400,
            }}
          >
            {p}
          </button>
        )
      )}
      <button
        onClick={() => current < total && onChange(current + 1)}
        disabled={current >= total}
        style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          width: 32, height: 32, borderRadius: 6, cursor: current < total ? "pointer" : "not-allowed",
          border: "1px solid var(--sidebar-border)", background: "var(--card-bg)",
          color: current < total ? "var(--primary)" : "var(--text-secondary)",
        }}
        aria-label="next"
      >
        <RightOutlined />
      </button>
    </div>
  );
}
