import { access, cp, rm } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const apiDir = path.join(root, "app", "api");
const parked = path.join(root, ".api-parked-for-static-export");

async function exists(target) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

async function parkApiRoutes() {
  await rm(path.join(root, "app", ".api-parked-for-static-export"), { recursive: true, force: true });
  if (!(await exists(apiDir))) return;
  await rm(parked, { recursive: true, force: true });
  await cp(apiDir, parked, { recursive: true });
  await rm(apiDir, { recursive: true, force: true });
}

async function restoreApiRoutes() {
  if (!(await exists(parked))) return;
  if (!(await exists(apiDir))) {
    await cp(parked, apiDir, { recursive: true });
  }
  await rm(parked, { recursive: true, force: true });
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
  if (result.status === 0) {
    const out = path.join(root, "out");
    const landing = path.join(root, "public", "landing.html");
    const zac = path.join(root, "public", "app");
    if (await exists(landing)) {
      await cp(landing, path.join(out, "index.html"));
    }
    if (await exists(zac)) {
      await rm(path.join(out, "app"), { recursive: true, force: true });
      await cp(zac, path.join(out, "app"), { recursive: true });
    }
  }
} finally {
  await restoreApiRoutes();
}
