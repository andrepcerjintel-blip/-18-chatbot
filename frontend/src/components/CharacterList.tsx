import { Character } from "../api";

interface Props {
  characters: Character[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreateClick: () => void;
}

export default function CharacterList({ characters, selectedId, onSelect, onCreateClick }: Props) {
  return (
    <div className="character-list">
      <div className="character-list-header">
        <h2>Personagens</h2>
        <button onClick={onCreateClick}>+ Nova</button>
      </div>
      <ul>
        {characters.map((c) => (
          <li
            key={c.id}
            className={c.id === selectedId ? "selected" : ""}
            onClick={() => onSelect(c.id)}
          >
            <div className="avatar">{c.name.charAt(0).toUpperCase()}</div>
            <div>
              <div className="char-name">{c.name}</div>
              <div className="char-sub">{c.age} anos · sintética</div>
            </div>
          </li>
        ))}
        {characters.length === 0 && <li className="empty">Nenhuma personagem ainda.</li>}
      </ul>
    </div>
  );
}
