import { Message, mediaFileUrl } from "../api";

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isSystemBlock = message.safety_status === "BLOCK";
  const hasGeneratedImage = message.intent === "IMAGE_REQUEST" && Boolean(message.media_id);

  return (
    <div className={`bubble-row ${isUser ? "from-user" : "from-character"}`}>
      <div className={`bubble ${isSystemBlock ? "bubble-blocked" : ""}`}>
        {hasGeneratedImage ? (
          <img
            className="bubble-image"
            src={mediaFileUrl(message.media_id as string)}
            alt="Imagem gerada pela personagem"
            loading="lazy"
          />
        ) : (
          <div className="bubble-text">{message.content}</div>
        )}
      </div>
    </div>
  );
}
