#!/usr/bin/env python3
"""Auditoria do ambiente local (somente leitura, nao instala nada).

Coleta informacoes de SO, Python, Git, GPU, CUDA, RAM, disco, ComfyUI e
Node.js/npm sem instalar ou alterar drivers, CUDA Toolkit ou qualquer
componente critico do sistema. Campos nao detectaveis sao reportados como
UNKNOWN e nao interrompem a execucao deste script nem do projeto.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

UNKNOWN = "UNKNOWN"


def run(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def audit_os() -> dict:
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
    }


def audit_python() -> dict:
    return {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
    }


def audit_git() -> dict:
    version = run(["git", "--version"])
    return {"git_installed": version is not None, "git_version": version or UNKNOWN}


def audit_node() -> dict:
    node_version = run(["node", "--version"])
    npm_version = run(["npm", "--version"])
    return {
        "node_installed": node_version is not None,
        "node_version": node_version or UNKNOWN,
        "npm_installed": npm_version is not None,
        "npm_version": npm_version or UNKNOWN,
    }


def audit_gpu() -> dict:
    """Tenta detectar GPU NVIDIA via nvidia-smi. Nunca instala drivers."""
    result = {
        "gpu_detected": False,
        "gpu_model": UNKNOWN,
        "gpu_vram_gb": UNKNOWN,
        "nvidia_driver": UNKNOWN,
        "cuda_version_driver": UNKNOWN,
    }
    if shutil.which("nvidia-smi") is None:
        return result
    query = run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader",
        ]
    )
    if not query:
        return result
    first_line = query.splitlines()[0]
    parts = [p.strip() for p in first_line.split(",")]
    if len(parts) >= 3:
        result["gpu_detected"] = True
        result["gpu_model"] = parts[0]
        mem = parts[1].replace(" MiB", "")
        try:
            result["gpu_vram_gb"] = round(float(mem) / 1024, 1)
        except ValueError:
            result["gpu_vram_gb"] = UNKNOWN
        result["nvidia_driver"] = parts[2]
    cuda_line = run(["nvidia-smi"])
    if cuda_line and "CUDA Version" in cuda_line:
        for line in cuda_line.splitlines():
            if "CUDA Version" in line:
                try:
                    result["cuda_version_driver"] = line.split("CUDA Version:")[1].strip().split()[0]
                except IndexError:
                    pass
    return result


def audit_cuda_toolkit() -> dict:
    version = run(["nvcc", "--version"])
    return {"nvcc_found": version is not None, "nvcc_version": version or UNKNOWN}


def audit_pytorch() -> dict:
    try:
        import torch  # type: ignore

        return {
            "torch_installed": True,
            "torch_version": torch.__version__,
            "torch_cuda_available": torch.cuda.is_available(),
            "torch_cuda_version": torch.version.cuda or UNKNOWN,
        }
    except ImportError:
        return {
            "torch_installed": False,
            "torch_version": UNKNOWN,
            "torch_cuda_available": False,
            "torch_cuda_version": UNKNOWN,
        }


def audit_ram() -> dict:
    try:
        import psutil  # type: ignore

        return {"ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1)}
    except ImportError:
        if platform.system() == "Linux":
            try:
                with open("/proc/meminfo") as fh:
                    for line in fh:
                        if line.startswith("MemTotal"):
                            kb = int(line.split()[1])
                            return {"ram_total_gb": round(kb / (1024**2), 1)}
            except OSError:
                pass
        return {"ram_total_gb": UNKNOWN}


def audit_disk() -> dict:
    disks = {}
    for path in [".", str(Path.home())]:
        try:
            usage = shutil.disk_usage(path)
            disks[path] = round(usage.free / (1024**3), 1)
        except OSError:
            disks[path] = UNKNOWN
    return {"disk_free_gb": disks}


def audit_comfyui() -> dict:
    candidates = [
        Path.home() / "ComfyUI",
        Path("C:/ComfyUI") if platform.system() == "Windows" else Path("/opt/ComfyUI"),
        Path.cwd() / "ComfyUI",
    ]
    for c in candidates:
        if c.exists():
            return {"comfyui_installed": True, "comfyui_path": str(c)}
    return {"comfyui_installed": False, "comfyui_path": UNKNOWN}


def main() -> None:
    report = {
        **audit_os(),
        **audit_python(),
        **audit_git(),
        **audit_node(),
        **audit_gpu(),
        **audit_cuda_toolkit(),
        **audit_pytorch(),
        **audit_ram(),
        **audit_disk(),
        **audit_comfyui(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
