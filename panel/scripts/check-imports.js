/** 检查 src/ 下所有 JSX 文件：使用的符号是否都已导入 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(__dirname, "../src");

let hasError = false;

function checkFile(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const imports = {};

  const importRegex = /import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g;
  let match;
  while ((match = importRegex.exec(content)) !== null) {
    const symbols = match[1].split(",").map((s) => s.trim());
    const pkg = match[2];
    for (const sym of symbols) {
      imports[sym] = pkg;
    }
  }

  for (const [sym, pkg] of Object.entries(imports)) {
    const usageRegex = new RegExp(`\\b${sym}\\.`, "g");
    const usages = content.match(usageRegex);
    if (usages && usages.length > 0) {
      const importRegex2 = new RegExp(
        `import\\s*\\{[^}]*\\b${sym}\\b[^}]*\\}\\s*from\\s*['"]${pkg}['"]`,
      );
      const declared = content.match(importRegex2);
      if (!declared) {
        console.error(`❌ ${filePath}: "${sym}" 从 "${pkg}" 导入，但不在 import 声明中`);
        hasError = true;
      }
    }
  }
}

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== "node_modules") walk(full);
    else if (entry.name.endsWith(".jsx") || entry.name.endsWith(".js")) checkFile(full);
  }
}

walk(SRC);

if (hasError) {
  console.error("\n⚠️  导入检查发现错误，请修复后重新构建");
  process.exit(1);
} else {
  console.log("✅ 导入检查通过");
}
