import { access, rename } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const apiDir = path.join(root, "app", "api");
const parked = path.join(root, "app", ".api-parked-for-static-export");

async function exists(target) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

async function parkApiRoutes() {
  if (await exists(apiDir)) {
    if (await exists(parked)) {
      await rename(parked, `${parked}.old-${Date.now()}`);
    }
    await rename(apiDir, parked);
  }
}

async function restoreApiRoutes() {
  if (await exists(parked)) {
    if (!(await exists(apiDir))) {
      await rename(parked, apiDir);
    }
  }
}

await parkApiRoutes();
try {
  const result = spawnSync("npx", ["next", "build"], {
    cwd: root,
    stdio: "inherit",
    shell: true,
    env: {
      ...process.env,
      MA_DARWIN_STATIC_EXPORT: "1",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  });
  process.exitCode = result.status ?? 1;
} finally {
  await restoreApiRoutes();
}
