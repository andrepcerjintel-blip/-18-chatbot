# Arquitetura

## Fluxo de dados (POST /chat)

```
USER_INPUT (texto do usuário, sempre não confiável)
   │
   ▼
Chat UI (React)  ──POST /chat──▶  FastAPI (app.api.chat)
   │
   ▼
Conversation Engine (app.conversation.engine)
   │
   ├─▶ Intent Classifier (app.services.intent_classifier)
   │      regras deterministicas -> IntentResult (schema validado)
   │
   ├─▶ Safety Engine (app.safety.engine)            [SEMPRE executa]
   │      regras deterministicas, fail-closed -> SafetyResult
   │      BLOCK ⇒ resposta padrão de bloqueio, conversa continua
   │
   ├─▶ Character State (app.models.character_state)
   │      leitura/escrita de MUTABLE_FIELDS apenas (nunca Character)
   │
   ├─▶ Prompt Builder + LLM Provider (app.services.llm)
   │      DEVELOPER_RULES (personagem/estado) e USER_INPUT são
   │      passados como partes distintas, nunca concatenados
   │      indiscriminadamente
   │
   ├─▶ ImageProvider (app.media)                     [se IMAGE/VIDEO_REQUEST]
   │      NullImageProvider (padrão) ou ComfyUIProvider (stub)
   │      nunca lança exceção; sempre retorna status estruturado
   │
   ├─▶ Post-generation Safety Check (app.safety.engine)
   │      roda sobre a resposta do LLM e/ou metadata de mídia
   │
   ▼
ChatResponse (schema Pydantic)  ──▶  Chat UI
```

## Módulos e responsabilidades

| Módulo | Responsabilidade |
|---|---|
| `app.config` | Configuração via `.env`, nenhum segredo hardcoded. |
| `app.database` | Engine/Session SQLAlchemy, `init_db()`. |
| `app.models` | ORM (Character, PersonalityProfile, Conversation, CharacterState, Message, MediaAsset). |
| `app.schemas` | Contratos Pydantic (validação de entrada/saída, nunca texto livre executável). |
| `app.character.manager` | Único ponto de escrita de `Character`; reforça invariantes protegidas. |
| `app.safety` | Safety Engine + regras deterministicas; fail-closed. |
| `app.services.intent_classifier` | Classificação de intenção baseada em regras. |
| `app.services.llm` | Abstração de LLM (`stub`, `anthropic`); desacoplada do resto do app. |
| `app.media` | Abstração `ImageProvider` (`null`, `comfyui` stub); desacoplada do resto do app. |
| `app.conversation.engine` | Orquestrador central do fluxo acima. |
| `app.conversation.memory` | Short-term memory + resumo progressivo. |
| `app.api` | Endpoints FastAPI (characters, conversations, chat, media, health). |

## Desacoplamento do gerador de imagens

```
Conversation Engine ──▶ ImageProvider (interface abstrata)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            NullImageProvider    ComfyUIProvider
            (ativo por padrão)   (stub, HTTP p/ ComfyUI local)
```

Nenhum outro módulo (Conversation Engine, Safety Engine, Character Manager,
Chat UI) conhece detalhes do ComfyUI. Trocar o engine visual (ComfyUI →
Diffusers → outro) exige mudanças apenas dentro de `app/media/`.

## Separação de confiança

- `SYSTEM_STATE` / `DEVELOPER_RULES` (config, regras de personagem, estado)
  são gerados internamente e nunca vêm do usuário.
- `USER_INPUT` é sempre tratado como não confiável: nunca altera campos
  protegidos de `Character`, nunca é executado como código/comando, e é
  isolado do prompt de sistema ao chamar o LLM (ver `app/services/llm/*`).
