import click
from .commit_generator import ezcommit
import os

@click.command()
@click.option("-run", is_flag=True, help="Automatically commit all staged files with a generated message.")
@click.option("--path", default=".", help="Path to the git repository")
@click.option("--unified", is_flag=True, help="Commit all staged files together with a single unified message (same feature).")
def main(run, path, unified):
    """
    CLI entry point for autocommit.
    """
    if run:
        repo_path = os.path.abspath(path)
        ezcommit(repo_path, unified=unified)
    else:
        click.echo("Use the -run option to commit all staged files with a generated message.")
        click.echo("Add --unified flag to commit all files together with a single message.")

if __name__ == "__main__":
    main()
