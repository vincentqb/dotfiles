import argparse
import logging
import os
import re
from pathlib import Path
from string import Template
from typing import List


def build_cdr_map(home, candidates):
    """
    Maps "candidate to be linked to" to ("dotfile", "rendered candidate")
    """
    TEMPLATE = ".template"
    RENDERED = ".rendered"

    names = {}

    for candidate in candidates:
        name = candidate.name
        if not (name.startswith(".") or name.endswith(RENDERED)):
            # Add dot prefix and replace template when needed
            rendered = candidate.parent / re.sub(TEMPLATE + "$", RENDERED, name)
            dotfile = home / ("." + re.sub(TEMPLATE + "$", "", name))
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
                    logger.warning(f"File {rendered} already exists but doesn't match newly rendered content")
                    success = False
            else:
                if not dry_run:
                    with open(rendered, "w") as fp:
                        fp.write(content_candidate)
    return success


def install_links(candidates, dry_run):
    success = True

    for candidate, (dotfile, rendered) in candidates.items():
        if dotfile.exists():
            if dotfile.is_symlink():
                link = os.readlink(str(dotfile))
                if link == str(rendered):
                    logger.info(f"File {dotfile} links to {rendered} as expected")
                else:
                    logger.warning(f"File {dotfile} exists and points to {link} instead of {rendered}")
                    success = False
            else:
                logger.warning(f"File {dotfile} exists but is not a link")
                success = False
        else:
            if dry_run:
                logger.info(f"File {dotfile} would be created and linked to {rendered}")
            else:
                dotfile.symlink_to(rendered)
                logger.info(f"File {dotfile} created and links to {rendered}")

    return success


def install_folders(folders, dry_run):
    home = Path("~").expanduser().resolve()

    success = True
    for folder in folders:
        folder = Path(folder)
        folder = folder.expanduser().resolve()
        if folder.exists and folder.is_dir():
            candidates = sorted(folder.glob("*"))
            candidates = build_cdr_map(home, candidates)

            success1 = install_links(candidates, dry_run)
            success2 = render_candidates(candidates, dry_run)
            success = success and success1 and success2
        else:
            logger.warning(f"Folder {folder} does not exist")
            success = False

    return success


def main(subparser, folders):
    """
    Link dotfiles to files in given folders in an idempotent way.
    """
    if subparser == "install":
        logger.setLevel(logging.WARNING)

    success = install_folders(folders, dry_run=True)
    if subparser == "install" and not success:
        logger.error("No new dotfiles were not linked since there are warnings")
        raise SystemExit()

    if subparser == "install":
        install_folders(folders, dry_run=False)


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

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(CustomFormatter())

    logger.addHandler(ch)
    return logger


def parse_arguments():
    parser = argparse.ArgumentParser(description=install_folders.__doc__)
    subparsers = parser.add_subparsers(dest="subparser")

    parser_install = subparsers.add_parser("install")
    parser_install.add_argument("folders", nargs="+")

    parser_check = subparsers.add_parser("check")
    parser_check.add_argument("folders", nargs="+")

    arguments = parser.parse_args()
    return vars(arguments)


if __name__ == "__main__":
    logger = get_logger()
    arguments = parse_arguments()
    main(**arguments)
