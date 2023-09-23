import argparse
import os
from pathlib import Path
from string import Template
from typing import List


def build_map(home, candidates):
    names = {}

    TEMPLATE = ".template"
    RENDERED = ".rendered"

    for candidate in candidates:
        if candidate.name.startswith("."):
            continue
        if candidate.name.endswith(RENDERED):
            continue

        name = candidate.name
        if name.endswith(TEMPLATE):
            name_dotfile = "." + name[: -len(TEMPLATE)]
            name_rendered = name[: -len(TEMPLATE)] + RENDERED
        else:
            name_dotfile = "." + name
            name_rendered = name

        dotfile = home / name_dotfile
        rendered = candidate.parent / name_rendered
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
                    print(f"File {rendered} already exists but its content doesn't match new content")
                    success = False
            else:
                if not dry_run:
                    with open(rendered, "w") as fp:
                        fp.write(content_candidate)
                        print(f"Rendered {rendered}")
    return success


def make_links(candidates, dry_run):
    success = True

    for candidate, (dotfile, rendered) in candidates.items():
        if dotfile.exists():
            if dotfile.is_symlink():
                if dotfile.readlink() == rendered:
                    if not dry_run:
                        print(f"Installed previously: {dotfile} => {rendered}")
                else:
                    print(f"File {dotfile} exists but does not point to {rendered}")
                    success = False
            else:
                print(f"File {dotfile} exists and is not a link")
                success = False
        else:
            if not dry_run:
                dotfile.symlink_to(rendered)
                print(f"Created now: {dotfile} => {rendered}")

    return success


def parse_folder(folder):
    folder = Path(folder)
    folder = folder.expanduser().resolve()

    if folder.exists and folder.is_dir():
        success = True
    else:
        print(f"Folder {folder} does not exist")
        success = False
    return success, folder


def install_folder(folder: Path, dry_run):
    success, folder = parse_folder(folder)
    if not success:
        return success

    home = Path("~").expanduser().resolve()
    candidates = list(folder.glob("*"))
    candidates = build_map(home, candidates)

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
        raise SystemExit("dotfiles not installed since there were errors")

    if not dry_run:
        for folder in folders:
            install_folder(folder, dry_run)


def parse_arguments():
    parser = argparse.ArgumentParser(description=install_folders.__doc__)
    parser.add_argument("folders", nargs="+")
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)
    arguments = parser.parse_args()
    return vars(arguments)


if __name__ == "__main__":
    arguments = parse_arguments()
    install_folders(**arguments)
