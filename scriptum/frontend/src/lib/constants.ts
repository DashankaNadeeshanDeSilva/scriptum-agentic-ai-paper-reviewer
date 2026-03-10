/**
 * Default model options per LLM provider.
 * Used as fallbacks when live model lists are unavailable.
 */
export const PROVIDER_MODELS: Record<string, string[]> = {
  anthropic: ["claude-opus-4-6", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"],
  openai: ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
  ollama: ["llama2", "llama3.1:70b", "mistral", "codellama"],
};

/** Default model per provider. */
export const DEFAULT_MODELS: Record<string, string> = {
  anthropic: "claude-opus-4-6",
  openai: "gpt-4-turbo",
  ollama: "llama2",
};
