import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

const projectRoot = process.cwd();
const sourceRoot = path.join(projectRoot, "src");

const checks = [
  {
    name: "no browser token storage",
    pattern: /\b(?:localStorage|sessionStorage)\b/,
    message: "Do not use browser storage for auth tokens or session material.",
  },
  {
    name: "no direct API imports in base UI components",
    pattern: /from\s+["']@\/lib\/api/,
    message: "Base UI components must not contain API business logic.",
    include: (filePath) => filePath.includes(`${path.sep}src${path.sep}components${path.sep}ui${path.sep}`),
  },
  {
    name: "no direct fetch outside API client and service worker",
    pattern: /\bfetch\s*\(/,
    message: "Use the centralized API client for frontend API calls.",
    include: (filePath) =>
      !filePath.endsWith(`${path.sep}src${path.sep}lib${path.sep}api${path.sep}client.ts`) &&
      !filePath.endsWith(`${path.sep}public${path.sep}sw.js`),
  },
  {
    name: "no negative letter spacing",
    pattern: /letter-spacing\s*:\s*-/,
    message: "Do not use negative letter spacing in frontend CSS.",
  },
];

const files = [
  ...(await collectFiles(sourceRoot, [".ts", ".tsx", ".css"])),
  ...(await collectFiles(path.join(projectRoot, "public"), [".js"])),
];

const failures = [];

for (const filePath of files) {
  const content = await readFile(filePath, "utf8");

  for (const check of checks) {
    if (check.include && !check.include(filePath)) {
      continue;
    }

    if (check.pattern.test(content)) {
      failures.push(`${relative(filePath)}: ${check.name} - ${check.message}`);
    }
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Frontend lint passed for ${files.length} files.`);

async function collectFiles(directory, extensions) {
  const entries = await readdir(directory, { withFileTypes: true });
  const results = [];

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      results.push(...(await collectFiles(entryPath, extensions)));
    } else if (extensions.some((extension) => entry.name.endsWith(extension))) {
      results.push(entryPath);
    }
  }

  return results;
}

function relative(filePath) {
  return path.relative(projectRoot, filePath);
}
