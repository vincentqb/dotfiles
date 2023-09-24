import argparse
import logging
import os
import re
from pathlib import Path
from string import Template
from typing import List


def build_cdr_map(home, candidates):
    names = {}

    TEMPLATE = ".template"
    RENDERED = ".rendered"

    for candidate in candidates:
        name = candidate.name

        if name.startswith(".") or name.endswith(RENDERED):
            continue

        # Add dot prefix and replace template by rendered when needed
        rendered = candidate.parent / re.sub(TEMPLATE + "$", RENDERED, name)
        dotfile = home / ("." + name.removesuffix(TEMPLATE))

        names[candidate] = (dotfile, rendered)

    return names


def render_candidates(candidates, dry_run):
    success = True
    for candidate, (dotfile, rendered) in candidates.items():
        if candidate != rendered:
            with open(candidate, "r") as fp:
                content_candidate = fp.read()
            content_candidate = Template(content_candidate).safe_substitute(os.environ)
            if rendered.exists():
                with open(rendered, "r") as fp:
                    content_rendered = fp.read()
                if content_candidate != content_rendered:
                    logger.warning(f"File {rendered} already exists but its content doesn't match new content")
                    success = False
            else:
                if not dry_run:
                    with open(rendered, "w") as fp:
                        fp.write(content_candidate)
                        # logger.info(f"Rendered {rendered}")
    return success


def make_links(candidates, dry_run):
    success = True

    for candidate, (dotfile, rendered) in candidates.items():
        if dotfile.exists():
            if dotfile.is_symlink():
                if dotfile.readlink() == rendered:
                    if not dry_run:
                        logger.info(f"Installed already: {dotfile} => {rendered}")
                else:
                    logger.warning(f"File {dotfile} exists but does not point to {rendered}")
                    success = False
            else:
                logger.warning(f"File {dotfile} exists and is not a link")
                success = False
        else:
            if not dry_run:
                dotfile.symlink_to(rendered)
                logger.info(f"Created now: {dotfile} => {rendered}")

    return success


def parse_folder(folder):
    folder = Path(folder)
    folder = folder.expanduser().resolve()

    if folder.exists and folder.is_dir():
        success = True
    else:
        logger.warning(f"Folder {folder} does not exist")
        success = False
    return success, folder


def install_folder(folder: Path, dry_run):
    success, folder = parse_folder(folder)
    if not success:
        return success

    home = Path("~").expanduser().resolve()
    candidates = list(folder.glob("*"))
    candidates = build_cdr_map(home, candidates)

    success = make_links(candidates, dry_run)
    success = success and render_candidates(candidates, dry_run)
    if not success:
        return success

    return success


def install_folders(folders: List[Path], dry_run: bool = False):
    """
    Idempotently link dotiles to files in given folders.
    """
    success = True
    for folder in folders:
        success = success and install_folder(folder, True)
    if not success:
        logger.error("dotfiles not installed since there were warnings")
        raise SystemExit()

    if not dry_run:
        for folder in folders:
            install_folder(folder, dry_run)


def get_logger():
    class CustomFormatter(logging.Formatter):
        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format = "%(levelname)s - %(message)s"

        FORMATS = {
            logging.DEBUG: grey + format + reset,
            logging.INFO: grey + "%(message)s" + reset,
            logging.WARNING: yellow + format + reset,
            logging.ERROR: red + format + reset,
            logging.CRITICAL: bold_red + format + reset,
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    logger = logging.getLogger("pydot")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(CustomFormatter())

    logger.addHandler(ch)
    return logger


def parse_arguments():
    parser = argparse.ArgumentParser(description=install_folders.__doc__)
    parser.add_argument("folders", nargs="+")
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)
    arguments = parser.parse_args()
    return vars(arguments)


if __name__ == "__main__":
    arguments = parse_arguments()
    logger = get_logger()
    install_folders(**arguments)
