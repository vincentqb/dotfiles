import os
from pathlib import Path
from string import Template

import typer
from loguru import logger

app = typer.Typer(add_completion=False)

TEMPLATE = ".template"
RENDERED = ".rendered"


def build_map(home, files):
    names = {}
    for file in files:
        if file.name.startswith("."):
            continue

        name = file.name
        if name.endswith(TEMPLATE):
            name = name[: -len(TEMPLATE)] + RENDERED

        dotfile = home / name
        names[file] = dotfile

    return names


def render_files(files):
    for file, dotfile in files.items():
        if file.name.endswith(TEMPLATE):
            with open(file, "r") as fp:
                content = fp.read()
            content = Template(content).safe_substitute(os.environ)
            with open(dotfile, "w") as fp:
                # fp.write(content)
                pass


def check_links(files):
    results = {}
    for file, dotfile in files.items():
        # logger.debug(file)
        results[file] = True

        if dotfile.exists():
            if dotfile.is_symlink():
                # breakpoint()
                if dotfile.readlink() != file:
                    logger.warning(f"{dotfile} already exists and does not points to {file}")
                    results[file] = False
            else:
                logger.warning(f"{dotfile} already exists")
                results[file] = False

    return results


def make_links(files):
    for file, dotfile in files.items():
        if dotfile.exists():
            logger.info(f"Exists: {dotfile} => {file}")
        else:
            # dotfile.symlink_to(file)
            logger.info(f"Created: {dotfile} => {file}")


@app.command()
def install(folder: Path):
    folder = folder.expanduser().resolve()
    assert folder.exists() and folder.is_dir(), f"folder {folder} does not exist"

    home = Path("~").expanduser().resolve()
    files = list(folder.glob("*"))
    files = build_map(home, files)

    if not all(check_links(files).values()):
        raise RuntimeError("Cannot install dotfiles")

    render_files(files)
    # make_links(files)


if __name__ == "__main__":
    app()
