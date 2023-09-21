from pathlib import Path

import typer
from loguru import logger

app = typer.Typer(add_completion=False)

TEMPLATE = ".template"
RENDERED = ".rendered"


def check_symlinks(home, files):

    success = True
    for file in files:
        logger.debug(file)

        if file.name[: -len(TEMPLATE)] == TEMPLATE:
            name = file.name[: -len(TEMPLATE)] + RENDERED
        else:
            name = file.name

        dotfile = home / name
        if dotfile.exists():
            if dotfile.is_symlink():
                breakpoint()
                if dotfile.readlink() != file:
                    logger.warning(f"{dotfile} already exists and does not points to {file}")
                    success = False
            else:
                logger.warning(f"{dotfile} already exists")
                success = False

    return success


def make_symlinks(home, files):

    for file in files:
        dotfile = home / f"{file.name}"
        if dotfile.exists():
            logger.info(f"Exists: {dotfile} => {file}")
        else:
            # dotfile.symlink_to(file)
            logger.info(f"Created: {dotfile} => {file}")


@app.command()
def install(folder: Path):

    folder = folder.expanduser().resolve()
    assert folder.exists() and folder.is_dir(), f"{folder} does not exist"

    candidates = list(folder.glob("*"))
    home = Path("~").expanduser().resolve()

    if not check_symlinks(home, candidates):
        raise RuntimeError("Cannot install dotfiles")

    make_symlinks(home, candidates)


if __name__ == "__main__":
    app()
