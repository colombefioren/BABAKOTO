"""Set the document language for each section of the operator guide."""

from mkdocs.structure.pages import Page


def on_post_page(output: str, *, page: Page, **_: object) -> str:
    if page.file.src_uri.startswith("fr/"):
        return output.replace('<html lang="en"', '<html lang="fr"', 1)
    return output
