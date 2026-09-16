import { useEffect, useState } from "react";
import { api, Character, Conversation, HealthResponse } from "./api";
import CharacterList from "./components/CharacterList";
import CharacterCreateModal from "./components/CharacterCreateModal";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCharacters()
      .then(setCharacters)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Erro ao carregar personagens."));
    api.health().then(setHealth).catch(() => undefined);
  }, []);

  const selectedCharacter = characters.find((c) => c.id === selectedId) ?? null;

  const handleSelect = async (id: string) => {
    setSelectedId(id);
    const conv = await api.createConversation(id);
    setConversation(conv);
  };

  const handleCreateCharacter = async (payload: Record<string, unknown>) => {
    const created = await api.createCharacter(payload);
    setCharacters((prev) => [created, ...prev]);
    await handleSelect(created.id);
  };

  return (
    <div className="app-shell">
      <aside>
        <CharacterList
          characters={characters}
          selectedId={selectedId}
          onSelect={handleSelect}
          onCreateClick={() => setShowCreate(true)}
        />
        <button className="settings-btn" onClick={() => setShowSettings(true)}>
          ⚙ Configurações
        </button>
      </aside>

      <main>
        {loadError && <div className="chat-notice">{loadError}</div>}
        {selectedCharacter && conversation ? (
          <ChatWindow
            character={selectedCharacter}
            conversation={conversation}
            onConversationUpdate={setConversation}
          />
        ) : (
          <div className="placeholder">Selecione ou crie uma personagem para começar.</div>
        )}
      </main>

      {showCreate && (
        <CharacterCreateModal onClose={() => setShowCreate(false)} onCreate={handleCreateCharacter} />
      )}

      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Configurações (somente leitura)</h3>
            {health ? (
              <ul className="settings-list">
                <li>Ambiente: {health.app_env}</li>
                <li>LLM Provider: {health.llm_provider}</li>
                <li>
                  Gerador de mídia: {health.media_provider.name} (
                  {health.media_provider.available ? "disponível" : "não configurado"})
                </li>
                <li>GPU vendor: {health.hardware.vendor}</li>
                <li>GPU model: {health.hardware.model}</li>
                <li>VRAM: {health.hardware.vram_gb}</li>
                <li>Backend: {health.hardware.backend}</li>
                <li>Driver: {health.hardware.driver_version}</li>
                <li>Runtime: {health.hardware.runtime_version}</li>
              </ul>
            ) : (
              <p>Backend indisponível.</p>
            )}
            <div className="modal-actions">
              <button onClick={() => setShowSettings(false)}>Fechar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
