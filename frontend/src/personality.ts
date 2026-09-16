// Identificadores neutros em relacao a genero (espelham
// backend/app/personality/presets.py). A personalidade e independente do
// genero do personagem -- esta camada so traduz o identificador para um
// rotulo gramaticalmente adequado na apresentacao, nunca na logica.
export const PERSONALITY_PRESETS = [
  "SHY",
  "MODEST",
  "RESERVED",
  "ROMANTIC",
  "CASUAL",
  "PROVOCATIVE",
  "BOLD",
] as const;

export type PersonalityPreset = (typeof PERSONALITY_PRESETS)[number];

const DISPLAY_LABELS: Record<string, { male: string; female: string; neutral: string }> = {
  SHY: { male: "Tímido", female: "Tímida", neutral: "Tímide" },
  MODEST: { male: "Pudico", female: "Pudica", neutral: "Pudique" },
  RESERVED: { male: "Recatado", female: "Recatada", neutral: "Recatade" },
  ROMANTIC: { male: "Romântico", female: "Romântica", neutral: "Romântique" },
  CASUAL: { male: "Despojado", female: "Despojada", neutral: "Despojade" },
  PROVOCATIVE: { male: "Provocador", female: "Provocadora", neutral: "Provocante" },
  BOLD: { male: "Atirado", female: "Atirada", neutral: "Atirade" },
};

export function presetDisplayLabel(preset: string, gender: string): string {
  const labels = DISPLAY_LABELS[preset.toUpperCase()];
  if (!labels) return preset;
  if (gender === "male" || gender === "female") return labels[gender];
  return labels.neutral;
}
