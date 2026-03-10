import { describe, it, expect } from "vitest";
import { exportSettingsYaml, parseSettingsYaml } from "@/lib/settings-yaml";

describe("exportSettingsYaml", () => {
  it("masks API keys showing only last 4 chars", () => {
    const settings = {
      llm: {
        anthropic: {
          api_key: "sk-ant-1234567890abcdef",
          model: "claude-opus-4-6",
        },
      },
    };
    const yaml = exportSettingsYaml(settings);

    expect(yaml).toContain("****cdef");
    expect(yaml).not.toContain("sk-ant-1234567890abcdef");
    // Model should NOT be masked
    expect(yaml).toContain("claude-opus-4-6");
  });

  it("does not mask short values", () => {
    const settings = {
      llm: { anthropic: { api_key: "short" } },
    };
    const yaml = exportSettingsYaml(settings);
    // Short keys (<=8 chars) are not masked
    expect(yaml).toContain("short");
  });
});

describe("parseSettingsYaml", () => {
  it("parses valid YAML with known top-level keys", () => {
    const yamlContent = `
llm:
  default_provider: anthropic
mcp:
  perplexity:
    enabled: true
`;
    const result = parseSettingsYaml(yamlContent);

    expect(result.llm).toBeDefined();
    expect(result.mcp).toBeDefined();
  });

  it("rejects YAML with unknown top-level keys", () => {
    const yamlContent = `
llm:
  provider: anthropic
unknown_key:
  value: test
`;
    expect(() => parseSettingsYaml(yamlContent)).toThrow("Unknown top-level keys: unknown_key");
  });

  it("rejects non-object YAML", () => {
    expect(() => parseSettingsYaml("just a string")).toThrow("expected a mapping");
    expect(() => parseSettingsYaml("- item1\n- item2")).toThrow("expected a mapping");
  });
});
