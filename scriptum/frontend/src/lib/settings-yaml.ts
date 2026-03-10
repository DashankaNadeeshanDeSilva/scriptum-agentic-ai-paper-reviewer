import yaml from "js-yaml";

const VALID_TOP_KEYS = new Set(["llm", "mcp", "apis", "agents"]);

/**
 * Mask API keys for safe export — show only last 4 chars.
 */
function maskValue(val: unknown): unknown {
  if (typeof val === "string" && val.length > 8) {
    return "****" + val.slice(-4);
  }
  if (typeof val === "object" && val !== null && !Array.isArray(val)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(val as Record<string, unknown>)) {
      out[k] = k.toLowerCase().includes("key") || k.toLowerCase().includes("secret")
        ? maskValue(v)
        : typeof v === "object" && v !== null
          ? maskValue(v)
          : v;
    }
    return out;
  }
  return val;
}

/**
 * Convert settings object to YAML with API keys masked.
 */
export function exportSettingsYaml(settings: Record<string, unknown>): string {
  const masked = maskValue(settings) as Record<string, unknown>;
  return yaml.dump(masked, { indent: 2, lineWidth: 120, noRefs: true });
}

/**
 * Parse a YAML string and validate top-level keys.
 * Returns the parsed object or throws with a descriptive message.
 */
export function parseSettingsYaml(content: string): Record<string, unknown> {
  const parsed = yaml.load(content);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Invalid YAML: expected a mapping at the top level.");
  }
  const obj = parsed as Record<string, unknown>;
  const invalid = Object.keys(obj).filter((k) => !VALID_TOP_KEYS.has(k));
  if (invalid.length > 0) {
    throw new Error(`Unknown top-level keys: ${invalid.join(", ")}. Allowed: ${[...VALID_TOP_KEYS].join(", ")}`);
  }
  return obj;
}

/**
 * Trigger a browser file download with the given content.
 */
export function downloadYaml(content: string, filename = "scriptum-settings.yaml"): void {
  const blob = new Blob([content], { type: "text/yaml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
