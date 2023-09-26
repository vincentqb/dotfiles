import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from re import sub
from string import Template


def link(candidate, dotfile, rendered, dry_run):
    """
    Link dotfiles to files in given folders in an idempotent way.
    """

    # Create rendered file from template
    if candidate != rendered:
        with open(candidate, "r") as fp:
            content = Template(fp.read()).safe_substitute(os.environ)

        if rendered.exists():
            with open(rendered, "r") as fp:
                if content != fp.read():
                    logger.warning(f"File {rendered} already exists but doesn't match newly rendered content")
        else:
            if not dry_run:
                with open(rendered, "w") as fp:
                    fp.write(content)

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
        if not dry_run:
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
                if not dry_run:
                    dotfile.unlink()
                logger.info(f"File {dotfile} unlinked from {rendered}")
            else:
                logger.warning(f"File {dotfile} exists and points to {link} instead of {rendered}")
        else:
            logger.warning(f"File {dotfile} exists but is not a link")
    else:
        logger.warning(f"File {dotfile} does not exists")


def run_command_on_folders(command, home, folders, dry_run):
    home = Path(home).expanduser().resolve()
    if home.exists and home.is_dir():
        for folder in folders:
            folder = Path(folder).expanduser().resolve()
            if folder.exists and folder.is_dir():
                for candidate in sorted(folder.glob("*")):
                    name = candidate.name
                    if not (name.startswith(".") or name.endswith(".rendered")):
                        # Add dot prefix and replace template when needed
                        rendered = candidate.parent / sub(".template$", ".rendered", name)
                        dotfile = home / ("." + sub(".template$", "", name))
                        command(candidate, dotfile, rendered, dry_run)
            else:
                logger.warning(f"Folder {folder} does not exist")
    else:
        logger.warning(f"Folder {home} does not exist")


def try_then_run_command(command, home, folders, dry_run):
    """
    Manage links to dotfiles.
    """
    logger.setLevel(logging.INFO if dry_run else logging.WARNING)

    command = COMMANDS[command]
    run_command_on_folders(command, home, folders, dry_run=True)

    if logger.warning.counter > 0:
        logger.error("There were warnings, so exiting without changing dotfiles.")
        raise SystemExit()

    if not dry_run:
        run_command_on_folders(command, home, folders, dry_run=False)


def parse_arguments():
    parser = ArgumentParser(description=try_then_run_command.__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for key, func in COMMANDS.items():
        subparser = subparsers.add_parser(key, description=func.__doc__)
        subparser.add_argument("folders", nargs="+")
        subparser.add_argument("--home", nargs="?", default="~")
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
    try_then_run_command(**parse_arguments())
