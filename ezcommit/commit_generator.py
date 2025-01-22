import json
import git
from datetime import datetime
from logging import getLogger, FileHandler, Formatter
from groq import Groq
import os
import re
from dotenv import load_dotenv

load_dotenv()

PROMPT = """

Please take the following XML structure that represents file diffs:

```xml
{0}
```

Using this xml structure generate a **JSON structure** where the key is the file name and the value is the corresponding commit message based on the diff. Return **only** the JSON structure, with no other explanation.


Expected Output Format:

```json
{
    "file1.extension": "commit message based on the content of diff of file1",
    "file2.extension": "commit message based on the content of diff of file2"
}
```
"""

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


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


def generate_file_diffs(repo: git.Repo, staged_files: list):
    diffs = {}
    
    try:
        if repo.head.is_valid():
            for file_path in staged_files:
                diff = repo.git.diff("HEAD", file_path)
                diffs[file_path] = diff
        else:
            for file_path in staged_files:
                diffs[file_path] = f"No commits yet, comparing with empty state for {file_path}"
                
    except git.exc.InvalidGitRepositoryError:
        ezcommit_logger.error("Invalid Git repository")
    
    return diffs


def create_input_for_llm(diffs):
    """
    Create a structured input for the LLM from file diffs using XML structure.
    :param diffs: Dictionary where keys are file names and values are their diffs.
    :return: Structured XML string for LLM input.
    """
    xml_structure = "<diffs>\n"
    for file, diff in diffs.items():
        xml_structure += f"    <file name='{file}'>\n"
        xml_structure += f"        <diff>{diff}</diff>\n"
        xml_structure += "    </file>\n"
    xml_structure += "</diffs>"
    return xml_structure

def extract_json_structure(llm_output: str):
    """
    Extract the JSON structure from the LLM output.
    :param llm_output: LLM output containing the JSON structure.
    :return: JSON structure extracted from the LLM output.
    """
    json_structure = re.search(r'```(.*?)```', llm_output, re.DOTALL).group(1)
    return json_structure


def generate_commit_message(xml_str: str):
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(xml_str),
                }
            ],
            model=os.getenv("MODEL_NAME"),
            stream=False,
        )
        ezcommit_logger.info(f"Response from LLM: {response.choices[0].message.content}")
        return extract_json_structure(response.choices[0].message.content)
    except Exception as e:
        ezcommit_logger.error(f"Error in generating commit message: {e}")
        return None

def get_json_as_dict(json_str: str):
    """
    Convert JSON string to dictionary.
    :param json_str: JSON string to convert.
    :return: Dictionary representation of the JSON string.
    """
    return json.loads(json_str)


def commit_staged_files_with_messages(repo: git.Repo, file_commit_dict: dict):
    """
    Commit already staged files with their respective commit messages.
    :param repo: The Git repository object.
    :param file_commit_dict: Dictionary where keys are file paths and values are commit messages.
    """
    for file_path, commit_message in file_commit_dict.items():
        repo.index.commit(commit_message, paths=[file_path])
        
        ezcommit_logger.info(f"Committed {file_path} with message: '{commit_message}'")

def ezcommit(repo_path: str):
    """
    Automate the process of generating commit messages for staged files and committing them.
    :param repo_path: Path to the Git repository.
    """
    try:
        repo = git.Repo(repo_path)
        staged_files = get_staged_files(repo)
        ezcommit_logger.info(f"Staged files: {staged_files}")
        diffs = generate_file_diffs(repo, staged_files)
        ezcommit_logger.info(f"Generated diffs: {diffs}")
        xml_input = create_input_for_llm(diffs)
        ezcommit_logger.info(f"XML input for LLM: {xml_input}")
        json_message = generate_commit_message(xml_input)
        ezcommit_logger.info(f"Generated JSON message: {json_message}")
        file_commit_dict = get_json_as_dict(json_message)
        ezcommit_logger.info(f"File commit dictionary: {file_commit_dict}")
        commit_staged_files_with_messages(repo, file_commit_dict)
    except Exception as e:
        ezcommit_logger.error(f"Error in ezcommit process: {e}")


if __name__ == "__main__":
    ezcommit(r"C:\Users\HP\Music\ez-commit\TestGround")