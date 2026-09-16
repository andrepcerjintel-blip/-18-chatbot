import { useState } from "react";
import { PERSONALITY_PRESETS, presetDisplayLabel } from "../personality";

type Gender = "male" | "female" | "";

interface Props {
  onClose: () => void;
  onCreate: (payload: Record<string, unknown>) => Promise<void>;
}

export default function CharacterCreateModal({ onClose, onCreate }: Props) {
  const [name, setName] = useState("");
  const [age, setAge] = useState(24);
  // Propositalmente SEM valor inicial: o sistema nunca deve presumir um
  // genero (ex.: feminino) por padrao. O usuário precisa escolher.
  const [gender, setGender] = useState<Gender>("");
  const [preset, setPreset] = useState<string>("ROMANTIC");
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
    if (gender !== "male" && gender !== "female") {
      setError("Selecione o gênero do personagem (masculino ou feminino).");
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
        <h3>Novo personagem sintético</h3>
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
            <select value={gender} onChange={(e) => setGender(e.target.value as Gender)} required>
              <option value="" disabled>
                Selecione...
              </option>
              <option value="male">Masculino</option>
              <option value="female">Feminino</option>
            </select>
          </label>
          <label>
            Aparência
            <textarea value={appearance} onChange={(e) => setAppearance(e.target.value)} />
          </label>
          <label>
            Personalidade (preset inicial)
            <select value={preset} onChange={(e) => setPreset(e.target.value)}>
              {PERSONALITY_PRESETS.map((p) => (
                <option key={p} value={p}>
                  {presetDisplayLabel(p, gender || "neutral")}
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
