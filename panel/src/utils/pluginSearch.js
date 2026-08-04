import { pinyin } from "pinyin-pro";

const toFull = (text) =>
  pinyin(String(text || ""), { toneType: "none", type: "array" }).join("");
const toInitial = (text) =>
  pinyin(String(text || ""), { pattern: "first", toneType: "none", type: "array" }).join("");

export function buildSearchIndex(plugin) {
  const fields = [
    plugin.name,
    plugin.display_name,
    plugin.author,
    plugin.description,
    plugin.id,
    ...(plugin.tags || []),
  ];
  return {
    raw: fields.join(" ").toLowerCase(),
    full: fields.map(toFull).join(" ").toLowerCase(),
    initial: fields.map(toInitial).join(" ").toLowerCase(),
  };
}

export function matchPlugin(plugin, keyword) {
  const kw = keyword.trim().toLowerCase();
  if (!kw) return true;
  const index = buildSearchIndex(plugin);
  const kwFull = toFull(kw);
  return (
    index.raw.includes(kw) ||
    index.full.includes(kw) ||
    index.initial.includes(kw) ||
    index.full.includes(kwFull) ||
    index.initial.includes(kwFull)
  );
}
