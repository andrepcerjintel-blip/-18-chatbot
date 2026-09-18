"""ComfyUIProvider -- geracao real via ComfyUI local (Fase 2).

Fluxo: POST /prompt (enfileira) -> poll GET /history/{prompt_id} (aguarda
conclusao) -> GET /view (baixa bytes) -> salva em disco -> ImageResult.

Prioridades vinculantes (ver HARDWARE.md, GPU de 4 GB de VRAM):
  - batch_size=1 sempre (fixado em comfyui_workflow.py, nao configuravel);
  - resolucao/steps/sampler conservadores por padrao (ver Settings);
  - timeout configuravel, nunca trava a requisicao indefinidamente;
  - falha de qualquer tipo (ComfyUI fora do ar, OOM, timeout, erro de
    execucao) retorna ImageResult estruturado, NUNCA lanca excecao nem
    quebra a conversa.

Este modulo nunca deve presumir CUDA/NVIDIA diretamente -- a unica
decisao dependente de hardware (se o provider esta "configurado") vem de
app.hardware.get_hardware_profile(), nunca de checagem direta a
torch/CUDA aqui.
"""
from __future__ import annotations

import random
import time
import uuid
from pathlib import Path

import httpx

from app.config import get_settings
from app.hardware.profile import get_hardware_profile
from app.logging_config import logger
from app.media.comfyui_workflow import build_txt2img_workflow
from app.media.provider_base import ImageProvider
from app.schemas.media import ImageRequest, ImageResult, MediaStatus, ProviderHealth

_DEFAULT_NEGATIVE_PROMPT = (
    "lowres, worst quality, low quality, bad anatomy, extra limbs, deformed, "
    "watermark, text, signature, disfigured, empty room, no humans, no people, "
    "scenery only, architecture only, furniture only"
)
_POLL_INTERVAL_SECONDS = 1.0


class ComfyUIProvider(ImageProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.hardware = get_hardware_profile()

    def generate_image(self, request: ImageRequest) -> ImageResult:
        try:
            if not self.hardware.is_known:
                return self._not_configured(
                    "ComfyUI provider is set, but the hardware profile (GPU vendor/VRAM/backend) "
                    "is still UNKNOWN. Run scripts/audit_env.py on the target machine and update .env."
                )
            if not self.settings.image_model_path:
                return self._not_configured(
                    "ComfyUI provider is set, but no visual checkpoint (IMAGE_MODEL_PATH) "
                    "has been configured yet."
                )
            health = self.health_check()
            if not health.available:
                return self._not_configured(
                    f"ComfyUI is not reachable at {self.settings.comfyui_url}: {health.detail}"
                )
            return self._run_generation(request)
        except Exception:
            logger.exception("comfyui_provider_generate_image_exception")
            return ImageResult(
                status=MediaStatus.ERROR,
                message="Unexpected error while attempting image generation.",
                metadata={},
            )

    def _not_configured(self, message: str) -> ImageResult:
        return ImageResult(status=MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED, message=message, metadata={})

    def _run_generation(self, request: ImageRequest) -> ImageResult:
        base_url = self.settings.comfyui_url.rstrip("/")
        seed = request.seed if request.seed is not None else random.randint(0, 2**32 - 1)
        client_id = str(uuid.uuid4())

        workflow = build_txt2img_workflow(
            checkpoint=self.settings.image_model_path,
            positive_prompt=request.prompt_hint,
            negative_prompt=self.settings.comfyui_negative_prompt or _DEFAULT_NEGATIVE_PROMPT,
            width=self.settings.comfyui_width,
            height=self.settings.comfyui_height,
            steps=self.settings.comfyui_steps,
            cfg=self.settings.comfyui_cfg,
            sampler_name=self.settings.comfyui_sampler,
            scheduler=self.settings.comfyui_scheduler,
            seed=seed,
        )

        timeout = httpx.Timeout(self.settings.comfyui_timeout_seconds, connect=5.0)
        with httpx.Client(base_url=base_url, timeout=timeout) as client:
            try:
                queue_resp = client.post("/prompt", json={"prompt": workflow, "client_id": client_id})
            except httpx.HTTPError as exc:
                logger.warning("comfyui_queue_request_failed error=%s", exc)
                return ImageResult(
                    status=MediaStatus.ERROR,
                    message=f"Failed to queue generation on ComfyUI: {exc}",
                    metadata={},
                )

            if queue_resp.status_code != 200:
                detail = self._extract_error_detail(queue_resp)
                logger.warning("comfyui_queue_rejected status=%s detail=%s", queue_resp.status_code, detail)
                return ImageResult(
                    status=MediaStatus.ERROR,
                    message=f"ComfyUI rejected the generation request: {detail}",
                    metadata={"http_status": queue_resp.status_code},
                )

            prompt_id = queue_resp.json().get("prompt_id")
            if not prompt_id:
                return ImageResult(
                    status=MediaStatus.ERROR, message="ComfyUI did not return a prompt_id.", metadata={}
                )

            outcome = self._poll_for_images(client, prompt_id)

            if outcome is None:
                return ImageResult(
                    status=MediaStatus.ERROR,
                    message=(
                        f"Image generation timed out after {self.settings.comfyui_timeout_seconds:.0f}s. "
                        "This can happen on the first run (model loading into VRAM) or under heavy "
                        "VRAM/CPU pressure on a 4 GB GPU."
                    ),
                    metadata={"prompt_id": prompt_id},
                )
            if isinstance(outcome, str):
                lowered = outcome.lower()
                is_oom = "out of memory" in lowered or ("cuda" in lowered and "memory" in lowered)
                message = (
                    "ComfyUI ran out of GPU memory (CUDA OOM) during generation, even at the "
                    "conservative default settings for this 4 GB GPU. Close other GPU-heavy "
                    "applications and try again."
                    if is_oom
                    else f"ComfyUI reported an error during generation: {outcome[:300]}"
                )
                return ImageResult(status=MediaStatus.ERROR, message=message, metadata={"prompt_id": prompt_id})
            if not outcome:
                return ImageResult(
                    status=MediaStatus.ERROR,
                    message="ComfyUI finished the job but produced no image.",
                    metadata={"prompt_id": prompt_id},
                )

            try:
                image_bytes = self._download_image(client, outcome[0])
            except httpx.HTTPError as exc:
                logger.warning("comfyui_view_download_failed error=%s", exc)
                return ImageResult(
                    status=MediaStatus.ERROR, message=f"Failed to download generated image: {exc}", metadata={}
                )

        image_id = str(uuid.uuid4())
        file_path = self._save_image(request, image_id, image_bytes)

        return ImageResult(
            status=MediaStatus.SUCCESS,
            message="Image generated successfully.",
            image_id=image_id,
            file_path=str(file_path),
            metadata={
                "seed": seed,
                "model": self.settings.image_model_path,
                "workflow": "txt2img_basic_lowvram",
                "width": self.settings.comfyui_width,
                "height": self.settings.comfyui_height,
                "steps": self.settings.comfyui_steps,
                "sampler": self.settings.comfyui_sampler,
                "prompt_id": prompt_id,
            },
        )

    def _poll_for_images(self, client: httpx.Client, prompt_id: str) -> list[dict] | str | None:
        """Aguarda a conclusao do job. Retorna:
        - list[dict] com {filename, subfolder, type} em caso de sucesso;
        - str com a mensagem de erro se a execucao falhou no ComfyUI;
        - None se o timeout foi atingido sem conclusao.
        """
        deadline = time.monotonic() + self.settings.comfyui_timeout_seconds
        while time.monotonic() < deadline:
            try:
                resp = client.get(f"/history/{prompt_id}")
            except httpx.HTTPError as exc:
                logger.warning("comfyui_history_poll_failed error=%s", exc)
                time.sleep(_POLL_INTERVAL_SECONDS)
                continue

            if resp.status_code == 200:
                entry = resp.json().get(prompt_id)
                if entry:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error":
                        messages = [
                            str(m[1]) for m in status.get("messages", []) if isinstance(m, list) and len(m) > 1
                        ]
                        return "; ".join(messages) or "unknown execution error"

                    for node_output in entry.get("outputs", {}).values():
                        node_images = node_output.get("images")
                        if node_images:
                            return node_images

                    if status.get("completed"):
                        return []

            time.sleep(_POLL_INTERVAL_SECONDS)
        return None

    def _download_image(self, client: httpx.Client, image_info: dict) -> bytes:
        params = {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
        resp = client.get("/view", params=params)
        resp.raise_for_status()
        return resp.content

    def _save_image(self, request: ImageRequest, image_id: str, image_bytes: bytes) -> Path:
        target_dir = Path(self.settings.generated_dir) / request.character_id / request.conversation_id
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{image_id}.png"
        file_path.write_bytes(image_bytes)
        return file_path

    @staticmethod
    def _extract_error_detail(resp: httpx.Response) -> str:
        try:
            data = resp.json()
            return str(data.get("error", data))[:300]
        except ValueError:
            return resp.text[:300]

    def health_check(self) -> ProviderHealth:
        base_url = self.settings.comfyui_url.rstrip("/")
        try:
            resp = httpx.get(f"{base_url}/system_stats", timeout=2.0)
            if resp.status_code == 200:
                return ProviderHealth(available=True, provider="comfyui", detail="reachable")
            return ProviderHealth(
                available=False, provider="comfyui", detail=f"unexpected status {resp.status_code}"
            )
        except httpx.HTTPError as exc:
            return ProviderHealth(available=False, provider="comfyui", detail=str(exc))
