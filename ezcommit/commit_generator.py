import git
from datetime import datetime
from logging import getLogger, FileHandler, Formatter
import os



###### generator logger ######
ezcommit_logger = getLogger("ezcommit-generator")
ezcommit_logger.setLevel("INFO")
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, "ezcommit-generator.log")
ezcommit_logger.addHandler(FileHandler(log_file, mode='w'))
ezcommit_logger.info(f"Logging to file: {log_file}")

# Set the log format
log_format = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ezcommit_logger.handlers[0].setFormatter(log_format)

###### generator logger ######



def get_staged_files(repo: git.Repo):
    """
    Get a list of all files that are currently staged for commit.
    """
    if repo.bare:
        ezcommit_logger.error("The provided path is not a valid Git repository.")
        raise ValueError("The provided path is not a valid Git repository.")
    
    staged_files = repo.git.diff('--name-only', '--staged').split('\n')
    ezcommit_logger.info(f"Staged files: {staged_files}")

    return staged_files