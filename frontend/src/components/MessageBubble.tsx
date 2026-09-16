import { Message } from "../api";

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isSystemBlock = message.safety_status === "BLOCK";

  return (
    <div className={`bubble-row ${isUser ? "from-user" : "from-character"}`}>
      <div className={`bubble ${isSystemBlock ? "bubble-blocked" : ""}`}>
        <div className="bubble-text">{message.content}</div>
        {message.intent === "IMAGE_REQUEST" && (
          <div className="bubble-media-note">📷 {message.content}</div>
        )}
      </div>
    </div>
  );
}
