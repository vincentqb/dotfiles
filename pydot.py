import os
from pathlib import Path
from string import Template

import typer
from loguru import logger

app = typer.Typer(add_completion=False)

TEMPLATE = ".template"
RENDERED = ".rendered"


def build_map(home, candidates):
    names = {}

    for candidate in candidates:
        if candidate.name.startswith("."):
            continue
        if candidate.name.endswith(RENDERED):
            continue

        name = candidate.name
        if name.endswith(TEMPLATE):
            name_dotfile = name[: -len(TEMPLATE)]
            name_rendered = name[: -len(TEMPLATE)] + RENDERED
        else:
            name_dotfile = name_rendered = name

        dotfile = home / name_dotfile
        rendered = home / name_rendered
        names[candidate] = (dotfile, rendered)

    return names


def render_candidates(candidates, dry_run):
    for candidate, (dotfile, rendered) in candidates.items():
        if candidate.name.endswith(TEMPLATE):
            with open(candidate, "r") as fp:
                content = fp.read()
            content = Template(content).safe_substitute(os.environ)
            with open(rendered, "w") as fp:
                if not dry_run:
                    fp.write(content)


def make_links(candidates, dry_run):
    success = True

    for file, (dotfile, rendered) in candidates.items():
        if dotfile.exists():
            if dotfile.is_symlink():
                if dotfile.readlink() == rendered:
                    if not dry_run:
                        logger.info(f"Exists: {dotfile} => {rendered}")
                else:
                    logger.warning(f"{dotfile} already exists and does not points to {file}")
                    success = False
            else:
                logger.warning(f"{dotfile} already exists")
                success = False
        else:
            if not dry_run:
                dotfile.symlink_to(rendered)
                logger.info(f"Created: {dotfile} => {rendered}")

    return success


@app.command()
def install(folder: Path, dry_run: bool = False):
    folder = folder.expanduser().resolve()
    assert folder.exists() and folder.is_dir(), f"folder {folder} does not exist"

    home = Path("~").expanduser().resolve()
    candidates = list(folder.glob("*"))
    candidates = build_map(home, candidates)

    if not make_links(candidates, dry_run):
        raise RuntimeError("Cannot install dotfiles")

    render_candidates(candidates, dry_run)
    make_links(candidates, dry_run)


if __name__ == "__main__":
    app()
