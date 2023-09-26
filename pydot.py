import argparse
import logging
import os
import re
from pathlib import Path
from string import Template


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


def link_render(candidate, dotfile, rendered, dry_run):
    if candidate != rendered:
        with open(candidate, "r") as fp:
            content_candidate = fp.read()
        content_candidate = Template(content_candidate).safe_substitute(os.environ)

        if rendered.exists():
            with open(rendered, "r") as fp:
                content_rendered = fp.read()
            if content_candidate != content_rendered:
                logger.warning(f"File {rendered} already exists but doesn't match newly rendered content")
                return False
        else:
            if not dry_run:
                with open(rendered, "w") as fp:
                    fp.write(content_candidate)
    return True


def link_make(candidate, dotfile, rendered, dry_run):
    if dotfile.exists():
        if dotfile.is_symlink():
            link = os.readlink(str(dotfile))
            if link == str(rendered):
                logger.info(f"File {dotfile} links to {rendered} as expected")
            else:
                logger.warning(f"File {dotfile} exists and points to {link} instead of {rendered}")
                return False
        else:
            logger.warning(f"File {dotfile} exists but is not a link")
            return False
    else:
        if dry_run:
            logger.info(f"File {dotfile} would be created and linked to {rendered}")
        else:
            dotfile.symlink_to(rendered)
            logger.info(f"File {dotfile} created and linked to {rendered}")
    return True


def link(candidates, dry_run):
    success = True

    for candidate, (dotfile, rendered) in candidates.items():
        success = all(
            [
                success,
                link_render(candidate, dotfile, rendered, dry_run),
                link_make(candidate, dotfile, rendered, dry_run),
            ]
        )

    return success


def unlink(candidates, dry_run):
    success = True

    for candidate, (dotfile, rendered) in candidates.items():
        if dotfile.exists():
            if dotfile.is_symlink():
                link = os.readlink(str(dotfile))
                if link == str(rendered):
                    if dry_run:
                        logger.info(f"File {dotfile} would be unlinked from {rendered}")
                    else:
                        dotfile.unlink()
                        logger.info(f"File {dotfile} unlinked from {rendered}")
                else:
                    logger.warning(f"File {dotfile} exists and points to {link} instead of {rendered}")
                    success = False
            else:
                logger.warning(f"File {dotfile} exists but is not a link")
                success = False
        else:
            logger.warning(f"File {dotfile} does not exists")
            success = False

    return success


def apply_command_to_folders(command, folders, dry_run):
    home = Path("~").expanduser().resolve()

    success = True
    for folder in folders:
        folder = Path(folder)
        folder = folder.expanduser().resolve()
        if folder.exists and folder.is_dir():
            candidates = sorted(folder.glob("*"))
            candidates = build_cdr_map(home, candidates)
            success = all([success, command(candidates, dry_run)])
        else:
            logger.warning(f"Folder {folder} does not exist")
            success = False

    return success


def main(command, folders, dry_run):
    """
    Link dotfiles to files in given folders in an idempotent way.
    """
    if not dry_run:
        logger.setLevel(logging.WARNING)

    command = COMMANDS[command]
    if not apply_command_to_folders(command, folders, dry_run=True):
        logger.error("dotfiles were not changed since there were warnings")
        raise SystemExit()
    if not dry_run:
        apply_command_to_folders(command, folders, dry_run=False)


def parse_arguments():
    parser = argparse.ArgumentParser(description=link.__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in COMMANDS.keys():
        parser_link = subparsers.add_parser(command)
        parser_link.add_argument("folders", nargs="+")
        parser_link.add_argument("--dry-run", default=False, action="store_true")
        parser_link.add_argument("--no-dry-run", dest="dry_run", action="store_false")

    arguments = parser.parse_args()
    return vars(arguments)


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


COMMANDS = {"link": link, "unlink": unlink}

if __name__ == "__main__":
    logger = get_logger()
    arguments = parse_arguments()
    main(**arguments)
