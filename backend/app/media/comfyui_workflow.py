"""Construtor do grafo de workflow no formato API do ComfyUI.

Workflow minimo de txt2img (CheckpointLoaderSimple -> CLIPTextEncode x2 ->
EmptyLatentImage -> KSampler -> VAEDecode -> SaveImage), equivalente ao
exemplo oficial `script_examples/basic_api_example.py` do proprio
ComfyUI. Mantido isolado do HTTP client (comfyui_provider.py) para poder
ser testado sem rede.

batch_size e sempre 1 (hardcoded, nao configuravel) -- restricao
vinculante para a GPU de 4 GB de VRAM (ver HARDWARE.md).
"""
from __future__ import annotations

_FIXED_BATCH_SIZE = 1


def build_txt2img_workflow(
    *,
    checkpoint: str,
    positive_prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    seed: int,
    filename_prefix: str = "companion",
) -> dict:
    return {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": _FIXED_BATCH_SIZE},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive_prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["4", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["8", 0]},
        },
    }
