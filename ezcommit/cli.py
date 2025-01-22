import click
from .commit_generator import ezcommit
import os

@click.command()
@click.option("-run", is_flag=True, help="Automatically commit all staged files with a generated message.")
@click.option("--path", default=".", help="Path to the git repository")
def main(run, path):
    """
    CLI entry point for autocommit.
    """
    if run:
        repo_path = os.path.abspath(path)
        ezcommit(repo_path)
    else:
        click.echo("Use the -run option to commit all staged files with a generated message.")

if __name__ == "__main__":
    main()
