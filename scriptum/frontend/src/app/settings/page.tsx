"use client";

import { useState } from "react";
import {
  Bot,
  Globe,
  Key,
  Sliders,
  Wrench,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

/* ------------------------------------------------------------------ */
/*  Mock settings — connected to backend API in Phase 4               */
/* ------------------------------------------------------------------ */

interface ProviderState {
  enabled: boolean;
  key: string;
  showKey: boolean;
  model: string;
  testStatus: "idle" | "testing" | "success" | "error";
}

const defaultProviders: Record<string, ProviderState> = {
  anthropic: {
    enabled: true,
    key: "",
    showKey: false,
    model: "claude-opus-4-6",
    testStatus: "idle",
  },
  openai: {
    enabled: false,
    key: "",
    showKey: false,
    model: "gpt-4-turbo",
    testStatus: "idle",
  },
  ollama: {
    enabled: false,
    key: "",
    showKey: false,
    model: "llama2",
    testStatus: "idle",
  },
};

const providerModels: Record<string, string[]> = {
  anthropic: ["claude-opus-4-6", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"],
  openai: ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
  ollama: ["llama2", "llama3.1:70b", "mistral", "codellama"],
};

/* ------------------------------------------------------------------ */
/*  Settings tabs                                                     */
/* ------------------------------------------------------------------ */

const tabs = [
  { value: "llm", label: "LLM", icon: Bot },
  { value: "mcp", label: "MCP", icon: Globe },
  { value: "apis", label: "APIs", icon: Key },
  { value: "preferences", label: "Preferences", icon: Sliders },
  { value: "advanced", label: "Advanced", icon: Wrench },
];

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function SettingsPage() {
  const [defaultProvider, setDefaultProvider] = useState("anthropic");
  const [providers, setProviders] = useState(defaultProviders);

  const updateProvider = (
    name: string,
    update: Partial<ProviderState>
  ) => {
    setProviders((prev) => ({
      ...prev,
      [name]: { ...prev[name], ...update },
    }));
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="font-heading mb-6 text-xl font-bold tracking-tight">
        Settings
      </h1>

      <Tabs defaultValue="llm" className="flex flex-col gap-6 sm:flex-row">
        {/* Sidebar tabs */}
        <TabsList className="flex h-auto flex-row justify-start gap-1 bg-transparent p-0 sm:flex-col sm:w-44">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className="justify-start gap-2 data-[state=active]:bg-muted"
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="flex-1">
          {/* ── LLM Tab ── */}
          <TabsContent value="llm" className="mt-0 space-y-6">
            <div>
              <Label className="text-sm font-medium">Default Provider</Label>
              <RadioGroup
                value={defaultProvider}
                onValueChange={setDefaultProvider}
                className="mt-2 flex gap-4"
              >
                {["anthropic", "openai", "ollama"].map((p) => (
                  <div key={p} className="flex items-center gap-2">
                    <RadioGroupItem value={p} id={`provider-${p}`} />
                    <Label htmlFor={`provider-${p}`} className="capitalize">
                      {p}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            <Separator />

            {Object.entries(providers).map(([name, prov]) => (
              <Card key={name}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base capitalize">
                      {name}
                    </CardTitle>
                    <Switch
                      checked={prov.enabled}
                      onCheckedChange={(v) =>
                        updateProvider(name, { enabled: v })
                      }
                    />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {name !== "ollama" && (
                    <div className="space-y-2">
                      <Label>API Key</Label>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <Input
                            type={prov.showKey ? "text" : "password"}
                            placeholder={`Enter ${name} API key`}
                            value={prov.key}
                            onChange={(e) =>
                              updateProvider(name, { key: e.target.value })
                            }
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                            onClick={() =>
                              updateProvider(name, {
                                showKey: !prov.showKey,
                              })
                            }
                          >
                            {prov.showKey ? (
                              <EyeOff className="h-3.5 w-3.5" />
                            ) : (
                              <Eye className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}

                  {name === "ollama" && (
                    <div className="space-y-2">
                      <Label>Base URL</Label>
                      <Input defaultValue="http://localhost:11434" />
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label>Model</Label>
                    <Select
                      value={prov.model}
                      onValueChange={(v) =>
                        updateProvider(name, { model: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(providerModels[name] ?? []).map((m) => (
                          <SelectItem key={m} value={m}>
                            {m}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        updateProvider(name, { testStatus: "testing" })
                      }
                    >
                      {prov.testStatus === "testing" ? (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      ) : null}
                      Test Connection
                    </Button>
                    {prov.testStatus === "success" && (
                      <Badge
                        variant="outline"
                        className="bg-success/10 text-success border-success/20"
                      >
                        <CheckCircle2 className="mr-1 h-3 w-3" />
                        Connected
                      </Badge>
                    )}
                    {prov.testStatus === "error" && (
                      <Badge
                        variant="outline"
                        className="bg-destructive/10 text-destructive border-destructive/20"
                      >
                        <XCircle className="mr-1 h-3 w-3" />
                        Failed
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* ── MCP Tab ── */}
          <TabsContent value="mcp" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Perplexity</CardTitle>
                <CardDescription>
                  Online search capabilities for literature discovery.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Enabled</Label>
                  <Switch />
                </div>
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input type="password" placeholder="pplx-..." />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Google Search</CardTitle>
                <CardDescription>
                  Custom search for supplementary reference discovery.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Enabled</Label>
                  <Switch />
                </div>
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input type="password" placeholder="AIza..." />
                </div>
                <div className="space-y-2">
                  <Label>Custom Search Engine ID (CX)</Label>
                  <Input placeholder="cx-..." />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── APIs Tab ── */}
          <TabsContent value="apis" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Semantic Scholar</CardTitle>
                <CardDescription>
                  Optional API key increases rate limits.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Input type="password" placeholder="API key (optional)" />
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">arXiv</p>
                  <p className="text-sm text-muted-foreground">
                    Open access preprint repository
                  </p>
                </div>
                <Switch defaultChecked />
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">CrossRef</p>
                  <p className="text-sm text-muted-foreground">
                    DOI resolution and metadata
                  </p>
                </div>
                <Switch defaultChecked />
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Preferences Tab ── */}
          <TabsContent value="preferences" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Defaults</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Default Journal Preset</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      <SelectItem value="ieee">IEEE TASLP</SelectItem>
                      <SelectItem value="nature">Nature</SelectItem>
                      <SelectItem value="neurips">NeurIPS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Advanced Tab ── */}
          <TabsContent value="advanced" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Configuration Management
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex gap-3">
                  <Button variant="outline" size="sm">
                    Export YAML
                  </Button>
                  <Button variant="outline" size="sm">
                    Import YAML
                  </Button>
                </div>
                <Separator />
                <div className="text-sm text-muted-foreground">
                  <p>
                    Config file:{" "}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                      ~/.scriptum/config.yaml
                    </code>
                  </p>
                  <p className="mt-1">
                    Encryption key:{" "}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                      ~/.scriptum/.key
                    </code>
                  </p>
                </div>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Environment Variables</p>
                  <div className="rounded-lg bg-muted/50 p-3 font-mono text-xs space-y-1">
                    <p>ANTHROPIC_API_KEY</p>
                    <p>OPENAI_API_KEY</p>
                    <p>OLLAMA_BASE_URL</p>
                    <p>PERPLEXITY_API_KEY</p>
                    <p>GOOGLE_SEARCH_API_KEY</p>
                    <p>SEMANTIC_SCHOLAR_API_KEY</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>

      {/* Save button */}
      <div className="mt-8 flex justify-end">
        <Button>Save Settings</Button>
      </div>
    </div>
  );
}
