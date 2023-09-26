import argparse
import logging
import os
import re
from pathlib import Path
from string import Template


def link(candidate, dotfile, rendered, dry_run):
    """
    Link dotfiles to files in given folders in an idempotent way.
    """

    # Create rendered file from template

    if candidate != rendered:
        with open(candidate, "r") as fp:
            content_candidate = fp.read()
        content_candidate = Template(content_candidate).safe_substitute(os.environ)

        if rendered.exists():
            with open(rendered, "r") as fp:
                content_rendered = fp.read()
            if content_candidate != content_rendered:
                logger.warning(f"File {rendered} already exists but doesn't match newly rendered content")
        else:
            if not dry_run:
                with open(rendered, "w") as fp:
                    fp.write(content_candidate)

    # Create link

    if dotfile.exists():
        if dotfile.is_symlink():
            link = os.readlink(str(dotfile))
            if link == str(rendered):
                logger.info(f"File {dotfile} links to {rendered} as expected")
            else:
                logger.warning(f"File {dotfile} exists and points to {link} instead of {rendered}")
        else:
            logger.warning(f"File {dotfile} exists but is not a link")
    else:
        if dry_run:
            logger.info(f"File {dotfile} would be created and linked to {rendered}")
        else:
            dotfile.symlink_to(rendered)
            logger.info(f"File {dotfile} created and linked to {rendered}")


def unlink(candidate, dotfile, rendered, dry_run):
    """
    Unlink dotfiles that are linked to files in given folders.
    """

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
        else:
            logger.warning(f"File {dotfile} exists but is not a link")
    else:
        logger.warning(f"File {dotfile} does not exists")


def apply_command_to_folders(home, command, folders, dry_run):
    home = Path(home).expanduser().resolve()
    for folder in folders:
        folder = Path(folder).expanduser().resolve()
        if folder.exists and folder.is_dir():
            for candidate in sorted(folder.glob("*")):
                name = candidate.name
                if not (name.startswith(".") or name.endswith(".rendered")):
                    # Add dot prefix and replace template when needed
                    rendered = candidate.parent / re.sub(".template$", ".rendered", name)
                    dotfile = home / ("." + re.sub(".template$", "", name))
                    command(candidate, dotfile, rendered, dry_run)
        else:
            logger.warning(f"Folder {folder} does not exist")


def main(command, folders, dry_run):
    """
    Manage links to dotfiles.
    """
    if not dry_run:
        logger.setLevel(logging.WARNING)

    home = "~"
    command = COMMANDS[command]

    apply_command_to_folders(home, command, folders, dry_run=True)

    if logger.warning.counter > 0:
        logger.error("dotfiles were not changed since there were warnings")
        raise SystemExit()

    if not dry_run:
        apply_command_to_folders(home, command, folders, dry_run=False)


def parse_arguments():
    parser = argparse.ArgumentParser(description=main.__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for key, func in COMMANDS.items():
        subparser = subparsers.add_parser(key, description=func.__doc__)
        subparser.add_argument("folders", nargs="+")
        subparser.add_argument("-d", "--dry-run", default=False, action="store_true")
        subparser.add_argument("--no-dry-run", dest="dry_run", action="store_false")

    return vars(parser.parse_args())


def get_logger():
    class CallCounted:
        """Decorator to determine number of calls for a method"""

        def __init__(self, method):
            self.method = method
            self.counter = 0

        def __call__(self, *args, **kwargs):
            self.counter += 1
            return self.method(*args, **kwargs)

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

    # Add logger.warning.counter
    logger.warning = CallCounted(logger.warning)
    return logger


if __name__ == "__main__":
    COMMANDS = {"link": link, "unlink": unlink}
    logger = get_logger()
    main(**parse_arguments())
