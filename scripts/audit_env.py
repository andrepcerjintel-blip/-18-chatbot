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


def _empty_gpu_result() -> dict:
    return {
        "gpu_detected": False,
        "gpu_vendor": UNKNOWN,
        "gpu_model": UNKNOWN,
        "gpu_vram_gb": UNKNOWN,
        "gpu_backend": UNKNOWN,
        "gpu_driver_version": UNKNOWN,
        "cuda_version_driver": UNKNOWN,
    }


def _detect_nvidia() -> dict | None:
    """NVIDIA -> backend CUDA."""
    if shutil.which("nvidia-smi") is None:
        return None
    query = run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]
    )
    if not query:
        return None
    first_line = query.splitlines()[0]
    parts = [p.strip() for p in first_line.split(",")]
    if len(parts) < 3:
        return None

    result = _empty_gpu_result()
    result.update(
        {
            "gpu_detected": True,
            "gpu_vendor": "nvidia",
            "gpu_backend": "cuda",
            "gpu_model": parts[0],
            "gpu_driver_version": parts[2],
        }
    )
    mem = parts[1].replace(" MiB", "")
    try:
        result["gpu_vram_gb"] = round(float(mem) / 1024, 1)
    except ValueError:
        result["gpu_vram_gb"] = UNKNOWN

    cuda_line = run(["nvidia-smi"])
    if cuda_line and "CUDA Version" in cuda_line:
        for line in cuda_line.splitlines():
            if "CUDA Version" in line:
                try:
                    result["cuda_version_driver"] = line.split("CUDA Version:")[1].strip().split()[0]
                except IndexError:
                    pass
    return result


def _detect_amd() -> dict | None:
    """AMD -> backend ROCm. Deteccao best-effort via rocm-smi."""
    if shutil.which("rocm-smi") is None:
        return None
    name_out = run(["rocm-smi", "--showproductname"])
    mem_out = run(["rocm-smi", "--showmeminfo", "vram"])
    driver_out = run(["rocm-smi", "--showdriverversion"])
    if not name_out:
        return None

    result = _empty_gpu_result()
    result.update({"gpu_detected": True, "gpu_vendor": "amd", "gpu_backend": "rocm"})

    for line in name_out.splitlines():
        if ":" in line and "GPU" in line.upper():
            result["gpu_model"] = line.split(":", 1)[-1].strip()
            break
    if result["gpu_model"] == UNKNOWN and name_out.strip():
        result["gpu_model"] = name_out.strip().splitlines()[-1]

    if mem_out:
        for line in mem_out.splitlines():
            if "Total" in line and ":" in line:
                digits = "".join(c for c in line.split(":")[-1] if c.isdigit() or c == ".")
                if digits:
                    try:
                        # rocm-smi reporta em bytes por padrao.
                        result["gpu_vram_gb"] = round(float(digits) / (1024**3), 1)
                    except ValueError:
                        pass
                break

    if driver_out:
        result["gpu_driver_version"] = driver_out.strip().splitlines()[-1]

    return result


def _detect_intel() -> dict | None:
    """Intel -> backend XPU (oneAPI/Level Zero). Deteccao best-effort."""
    for tool in ("xpu-smi", "intel_gpu_top"):
        if shutil.which(tool) is not None:
            result = _empty_gpu_result()
            result.update(
                {"gpu_detected": True, "gpu_vendor": "intel", "gpu_backend": "xpu", "gpu_model": tool}
            )
            if tool == "xpu-smi":
                out = run(["xpu-smi", "discovery"])
                if out:
                    result["gpu_model"] = out.strip().splitlines()[0][:200]
            return result
    return None


def audit_gpu() -> dict:
    """Tenta detectar GPU de qualquer fabricante suportado (NVIDIA, AMD,
    Intel), sem presumir nenhum deles e sem instalar drivers. Se nenhum
    vendor for detectavel, todos os campos permanecem UNKNOWN e o backend
    sugerido e 'cpu' (fallback), sem bloquear o desenvolvimento."""
    for detector in (_detect_nvidia, _detect_amd, _detect_intel):
        detected = detector()
        if detected is not None:
            return detected

    result = _empty_gpu_result()
    result["gpu_backend"] = "cpu"
    return result


def audit_cuda_toolkit() -> dict:
    version = run(["nvcc", "--version"])
    return {"nvcc_found": version is not None, "nvcc_version": version or UNKNOWN}


def audit_pytorch() -> dict:
    """Reporta o que o PyTorch ja instalado enxerga, sem instalar nada.
    torch.cuda cobre tanto builds CUDA (NVIDIA) quanto builds ROCm (AMD,
    que reutilizam a mesma API); torch.xpu cobre Intel em versoes recentes."""
    try:
        import torch  # type: ignore

        result = {
            "torch_installed": True,
            "torch_version": torch.__version__,
            "torch_cuda_available": torch.cuda.is_available(),
            "torch_cuda_version": torch.version.cuda or UNKNOWN,
            "torch_hip_version": getattr(torch.version, "hip", None) or UNKNOWN,
            "torch_xpu_available": bool(getattr(torch, "xpu", None) and torch.xpu.is_available()),
        }
        return result
    except ImportError:
        return {
            "torch_installed": False,
            "torch_version": UNKNOWN,
            "torch_cuda_available": False,
            "torch_cuda_version": UNKNOWN,
            "torch_hip_version": UNKNOWN,
            "torch_xpu_available": False,
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
