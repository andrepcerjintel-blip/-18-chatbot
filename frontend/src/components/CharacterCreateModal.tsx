import { useState } from "react";

const PRESETS = ["timida", "pudica", "recatada", "romantica", "despojada", "provocadora", "atirada"];

interface Props {
  onClose: () => void;
  onCreate: (payload: Record<string, unknown>) => Promise<void>;
}

export default function CharacterCreateModal({ onClose, onCreate }: Props) {
  const [name, setName] = useState("");
  const [age, setAge] = useState(24);
  const [gender, setGender] = useState("feminino");
  const [preset, setPreset] = useState("romantica");
  const [appearance, setAppearance] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (age < 21) {
      setError("A idade mínima permitida é 21 anos.");
      return;
    }
    setSubmitting(true);
    try {
      await onCreate({
        name,
        age,
        gender,
        appearance,
        personality_preset: preset,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar personagem.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Nova personagem sintética</h3>
        <form onSubmit={handleSubmit}>
          <label>
            Nome
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Idade (mínimo 21)
            <input
              type="number"
              min={21}
              value={age}
              onChange={(e) => setAge(Number(e.target.value))}
              required
            />
          </label>
          <label>
            Gênero
            <input value={gender} onChange={(e) => setGender(e.target.value)} required />
          </label>
          <label>
            Aparência
            <textarea value={appearance} onChange={(e) => setAppearance(e.target.value)} />
          </label>
          <label>
            Personalidade (preset inicial)
            <select value={preset} onChange={(e) => setPreset(e.target.value)}>
              {PRESETS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          {error && <div className="form-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" disabled={submitting}>
              {submitting ? "Criando..." : "Criar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
