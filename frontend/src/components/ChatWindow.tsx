import { useEffect, useRef, useState } from "react";
import { api, Character, Conversation } from "../api";
import MessageBubble from "./MessageBubble";

interface Props {
  character: Character;
  conversation: Conversation;
  onConversationUpdate: (c: Conversation) => void;
}

export default function ChatWindow({ character, conversation, onConversationUpdate }: Props) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [conversation.messages.length]);

  const handleSend = async () => {
    const text = draft.trim();
    if (!text || sending) return;
    setSending(true);
    setNotice(null);
    setDraft("");
    try {
      const response = await api.sendChat(conversation.id, text);
      const refreshed = await api.getConversation(conversation.id);
      onConversationUpdate(refreshed);

      if (response.media?.status === "MEDIA_PROVIDER_NOT_CONFIGURED") {
        setNotice("Geração de imagem local ainda não configurada neste ambiente.");
      } else if (response.safety_decision === "BLOCK") {
        setNotice("Pedido bloqueado pelas regras de segurança.");
      }
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Erro ao enviar mensagem.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="avatar large">{character.name.charAt(0).toUpperCase()}</div>
        <div>
          <div className="char-name">{character.name}</div>
          <div className="char-sub">
            {conversation.state.location} · {conversation.state.mood} · {conversation.state.outfit}
          </div>
        </div>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {conversation.messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {conversation.messages.length === 0 && (
          <div className="empty-chat">Diga olá para {character.name}.</div>
        )}
      </div>

      {notice && <div className="chat-notice">{notice}</div>}

      <div className="chat-footer">
        <input
          value={draft}
          placeholder="Escreva uma mensagem..."
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSend();
          }}
          disabled={sending}
        />
        <button onClick={handleSend} disabled={sending || !draft.trim()}>
          Enviar
        </button>
      </div>
    </div>
  );
}
