import os
from pathlib import Path
from string import Template


try:
    import typer

    app = typer.Typer(add_completion=False)
except ImportError:

    class App:
        def command(self):
            def func(command):
                self.func = command

            return func

        def __call__(self):
            import sys

            self.func(sys.argv[-1])

    app = App()


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
                        print(f"Exists: {dotfile} => {rendered}")
                else:
                    print(f"File {dotfile} exists but does not point to {rendered}")
                    success = False
            else:
                print(f"File {dotfile} exists and is not a link")
                success = False
        else:
            if not dry_run:
                dotfile.symlink_to(rendered)
                print(f"Created: {dotfile} => {rendered}")

    return success


@app.command()
def install(folder: Path, dry_run: bool = False):
    """
    Idempotently link dotiles to given files.
    """
    folder = Path(folder)
    folder = folder.expanduser().resolve()
    assert folder.exists() and folder.is_dir(), f"Folder {folder} does not exist"

    home = Path("~").expanduser().resolve()
    candidates = list(folder.glob("*"))
    candidates = build_map(home, candidates)

    success = make_links(candidates, True)
    success = success and render_candidates(candidates, True)
    if not success:
        raise SystemExit("There were warnings: dotfiles not installed")

    render_candidates(candidates, dry_run)
    make_links(candidates, dry_run)


if __name__ == "__main__":
    app()
