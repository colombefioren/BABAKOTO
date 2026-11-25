"""In-process training and WER comparison for a private Molab GPU workspace."""

import marimo

__generated_with = "0.26.0"
app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo

    return Path, mo


@app.cell
def _(mo):
    root = mo.ui.text(value="data/asr", label="Private corpus directory")
    manifest = mo.ui.text(value="data/asr/manifest.json", label="Prepared manifest")
    output = mo.ui.text(value="outputs/babakoto-asr", label="Local checkpoint directory")
    revision = mo.ui.text(label="Sunflower baseline revision")
    fit = mo.ui.run_button(label="Train on GPU")
    evaluate = mo.ui.run_button(label="Compare on held-out speech")
    mo.vstack([root, manifest, output, revision, fit, evaluate])
    return evaluate, fit, manifest, output, revision, root


@app.cell
def _(Path, fit, manifest, mo, output, root):
    from babakoto_training_asr.finetune import train

    mo.stop(not fit.value)
    train(Path(root.value), Path(manifest.value), Path(output.value))
    mo.md("Local checkpoint exported.")
    return


@app.cell
def _(evaluate, manifest, mo, output, revision, root):
    from babakoto_eval.wer import main

    mo.stop(not evaluate.value)
    main(
        [
            "--root",
            root.value,
            "--manifest",
            manifest.value,
            "--candidate",
            output.value,
            "--sunflower-revision",
            revision.value,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
