# /// script
# requires-python = ">=3.11"
# ///
"""Run the Babakoto latency benchmark on a GPU notebook (Molab).

Everything runs inside the notebook process, so it needs no Docker and no open ports: the STT and
TTS services start on localhost in background threads and the benchmark calls them over HTTP.

Status: written from Molab's public docs, NOT yet run there. The docs do not say whether the
notebook has a shell, outbound internet, or secret storage. If a cell fails for that reason, the
latency script itself (`python -m babakoto_eval.latency`) works on any machine with a GPU.
Keep credentials in the workspace's private .env file.
"""

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Babakoto latency benchmark

        1. Turn on a GPU in the notebook specs button (header).
        2. Configure the private `.env` with model revisions, keys and a consented reference voice.
        3. Run the cells top to bottom. The last cell prints p50 and p95.

        The TTS engine uses **non-commercial weights**: this notebook is for research only.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import subprocess
    import sys
    from pathlib import Path

    repo = Path("babakoto")
    if not repo.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/colombefioren/BABAKOTO.git",
                str(repo),
            ],
            check=True,
        )
    # Order matters: pip cannot resolve workspace members, so install dependencies first.
    for target in (
        "packages/common",
        "packages/malagasy-text",
        "services/stt[sunflower]",
        "services/tts[omnivoice]",
        "agent",
        "eval",
    ):
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-e", str(repo / target)], check=True
        )
    mo.md("Packages installed.")
    return Path, repo


@app.cell
def _(Path, mo, repo):
    import os

    import torch
    from dotenv import load_dotenv

    env_file = repo / ".env" if (repo / ".env").is_file() else Path(".env")
    mo.stop(not env_file.is_file(), mo.md("Configure the private .env before running."))
    load_dotenv(env_file)
    mo.stop(not torch.cuda.is_available(), mo.md("**No GPU detected.** Enable one and rerun."))
    gpu_name = torch.cuda.get_device_name(0)
    os.environ.update(
        {
            "STT_ENGINE": "sunflower",
            "TTS_ENGINE": "omnivoice",
            "STT_SERVICE_URL": "http://127.0.0.1:8001",
            "TTS_SERVICE_URL": "http://127.0.0.1:8002",
        }
    )
    mo.md(f"GPU: **{gpu_name}**")
    return (gpu_name,)


@app.cell
def _(gpu_name, mo):
    import threading
    import time

    import httpx
    import uvicorn

    from babakoto_stt.app import create_app_from_env as stt_app
    from babakoto_tts.app import create_app_from_env as tts_app

    def serve(factory, port):  # type: ignore[no-untyped-def]
        server = uvicorn.Server(
            uvicorn.Config(factory(), host="127.0.0.1", port=port, log_level="warning")
        )
        threading.Thread(target=server.run, daemon=True).start()
        return server

    assert gpu_name
    servers = [serve(stt_app, 8001), serve(tts_app, 8002)]
    deadline = time.time() + 900  # model downloads and loading can take minutes
    for port in (8001, 8002):
        while time.time() < deadline:
            try:
                if httpx.get(f"http://127.0.0.1:{port}/readyz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(3)
        else:
            raise TimeoutError(f"service on port {port} did not become ready")
    mo.md("STT and TTS services are ready.")
    return (servers,)


@app.cell
def _(gpu_name, mo, servers):
    import json

    from babakoto_eval.latency import main

    assert servers
    exit_code = main(["--turns", "50", "--gpu-name", gpu_name, "--out", "results/latency.json"])
    report = json.loads(open("results/latency.json", encoding="utf-8").read())  # noqa: SIM115
    mo.md(
        f"""
        **{report["turns"]} turns on {report["gpu"]}**

        | | p50 | p95 | target |
        |---|---|---|---|
        | total | {report["total_s"]["p50"]:.2f} s | {report["total_s"]["p95"]:.2f} s | 1.5 s / 2.5 s |
        | STT | {report["stages_s"]["stt"]["p50"]:.2f} s | {report["stages_s"]["stt"]["p95"]:.2f} s | |
        | LLM first sentence | {report["stages_s"]["llm_first_sentence"]["p50"]:.2f} s | {report["stages_s"]["llm_first_sentence"]["p95"]:.2f} s | |
        | TTS first audio | {report["stages_s"]["tts_first_audio"]["p50"]:.2f} s | {report["stages_s"]["tts_first_audio"]["p95"]:.2f} s | |

        Targets met: **{"yes" if exit_code == 0 else "no"}**. Download `results/latency.json`
        and attach it to the milestone issue.
        """
    )
    return


if __name__ == "__main__":
    app.run()
