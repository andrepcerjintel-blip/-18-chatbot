"""Servidor HTTP minimo que imita as rotas do ComfyUI usadas por
ComfyUIProvider (/system_stats, /prompt, /history/{id}, /view).

Usado apenas em testes, para validar a logica de integracao HTTP
(enfileirar, aguardar, baixar, tratar erro/OOM/timeout) sem depender de
uma instalacao real do ComfyUI ou de uma GPU.
"""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# PNG 1x1 transparente, valido de verdade (nao apenas bytes com a
# assinatura) -- permite que testes manuais/visuais no navegador
# renderizem uma imagem real em vez de um icone de imagem quebrada.
FAKE_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class MockComfyUIServer:
    def __init__(self) -> None:
        self.scenario = "success"  # success | error | oom | no_output | pending | reject
        self.received_prompts: list[dict] = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _make_handler(self):
        mock = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:  # silencia logs durante os testes
                pass

            def do_GET(self) -> None:  # noqa: N802 (nome exigido pelo BaseHTTPRequestHandler)
                if self.path == "/system_stats":
                    self._json(200, {"system": {}})
                elif self.path.startswith("/history/"):
                    prompt_id = self.path.split("/history/")[-1]
                    self._json(200, mock._history_response(prompt_id))
                elif self.path.startswith("/view"):
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.end_headers()
                    self.wfile.write(FAKE_PNG_BYTES)
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                if self.path == "/prompt":
                    length = int(self.headers.get("Content-Length", 0))
                    body = json.loads(self.rfile.read(length) or b"{}")
                    mock.received_prompts.append(body)
                    if mock.scenario == "reject":
                        self._json(400, {"error": "invalid prompt: missing required input"})
                        return
                    self._json(200, {"prompt_id": "test-prompt-id"})
                else:
                    self._json(404, {"error": "not found"})

            def _json(self, status: int, payload: dict) -> None:
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        return Handler

    def _history_response(self, prompt_id: str) -> dict:
        if self.scenario == "success":
            return {
                prompt_id: {
                    "status": {"status_str": "success", "completed": True, "messages": []},
                    "outputs": {
                        "9": {
                            "images": [
                                {"filename": "companion_00001_.png", "subfolder": "", "type": "output"}
                            ]
                        }
                    },
                }
            }
        if self.scenario == "oom":
            return {
                prompt_id: {
                    "status": {
                        "status_str": "error",
                        "completed": True,
                        "messages": [["execution_error", "CUDA out of memory. Tried to allocate 20.00 MiB"]],
                    },
                    "outputs": {},
                }
            }
        if self.scenario == "error":
            return {
                prompt_id: {
                    "status": {
                        "status_str": "error",
                        "completed": True,
                        "messages": [["execution_error", "some node failed"]],
                    },
                    "outputs": {},
                }
            }
        if self.scenario == "no_output":
            return {
                prompt_id: {
                    "status": {"status_str": "success", "completed": True, "messages": []},
                    "outputs": {},
                }
            }
        # "pending": nunca aparece no historico -> forca timeout no cliente.
        return {}
