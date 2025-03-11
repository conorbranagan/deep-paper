export interface ModelOption {
  id: string;
  name: string;
}

export const modelOptions: ModelOption[] = [
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'anthropic/claude-3-7-sonnet-latest', name: 'Claude 3.7 Sonnet' },
  { id: "anthropic/claude-3-5-sonnet-latest", name: "Claude 3.5 Sonnet" },
  { id: "anthropic/claude-3-5-haiku-latest", name: "Claude 3.5 Haiku" },
  { id: 'openai/gpt-4o', name: 'GPT-4o' },
  { id: 'vertex_ai/gemini-2.0-flash-001', name: 'Gemini 2.0 Flash' },
  { id: 'vertex_ai/gemini-2.0-flash-lite-001', name: 'Gemini 2.0 Flash Lite' },
  { id: 'vertex_ai/gemini-2.0-pro-exp-02-05', name: 'Gemini 2.0 Pro Exp 02-05' },
]; 