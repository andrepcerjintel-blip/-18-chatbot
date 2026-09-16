// O frontend fala apenas com o backend local (FastAPI). Nunca chama o
// ComfyUI (ou qualquer gerador de midia) diretamente -- o backend decide
// como/se a midia e gerada, mantendo o desacoplamento.
const BASE_URL = "http://127.0.0.1:8000";

export interface Personality {
  preset: string;
  shyness: number;
  extroversion: number;
  initiative: number;
  romanticism: number;
  sexual_openness: number;
  playfulness: number;
  assertiveness: number;
  affection: number;
}

export interface Character {
  id: string;
  name: string;
  age: number;
  synthetic: boolean;
  gender: string;
  appearance: string;
  hair: string;
  eyes: string;
  skin: string;
  height: string;
  body_description: string;
  distinctive_features: string;
  visual_identity_reference: string;
  created_at: string;
  personality: Personality;
}

export interface CharacterState {
  location: string;
  time_of_day: string;
  outfit: string;
  hair_state: string;
  mood: string;
  last_pose: string;
  last_generated_media: string | null;
  conversation_summary: string;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  intent: string | null;
  safety_status: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  character_id: string;
  created_at: string;
  updated_at: string;
  state: CharacterState;
  messages: Message[];
}

export interface MediaResult {
  status: string;
  message: string;
  image_id: string | null;
  file_path: string | null;
  metadata: Record<string, unknown>;
}

export interface ChatResponse {
  conversation_id: string;
  intent: string;
  safety_decision: string;
  safety_reasons: string[];
  reply: string | null;
  media: MediaResult | null;
  state: CharacterState | null;
}

export interface HealthResponse {
  status: string;
  app_env: string;
  llm_provider: string;
  media_provider: { name: string; available: boolean; detail: string };
  hardware: { gpu_model: string; gpu_vram_gb: string; cuda_version: string };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  listCharacters: () => request<Character[]>("/characters"),
  createCharacter: (payload: Record<string, unknown>) =>
    request<Character>("/characters", { method: "POST", body: JSON.stringify(payload) }),
  createConversation: (characterId: string) =>
    request<Conversation>("/conversations", {
      method: "POST",
      body: JSON.stringify({ character_id: characterId }),
    }),
  getConversation: (conversationId: string) =>
    request<Conversation>(`/conversations/${conversationId}`),
  sendChat: (conversationId: string, message: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, message }),
    }),
};
