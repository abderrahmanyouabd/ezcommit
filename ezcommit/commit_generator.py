import jsonc as json
import git
from datetime import datetime
from logging import getLogger, FileHandler, Formatter
from groq import Groq
import os
import re
from dotenv import load_dotenv
import sys

load_dotenv()

def get_prompt(xml_str):
    return f"""
    Please take the following XML structure that represents file diffs:
    ```xml
    {xml_str}
    ```
    Using this xml structure, generate a JSON structure enclosed with '```' where the key is the file name and the value is the corresponding commit message based on the diff. Return only the JSON structure, with no other explanation.
    Use Git commit standards and conventions for commit messages. <type>[optional scope]: <description>.
    Expected Output Format:
    ```json
    {{}}
    ```
    """

def get_unified_prompt(xml_str):
    return f"""
    Please take the following XML structure that represents file diffs for multiple files:
    ```xml
    {xml_str}
    ```
    Analyze all the changes across all files and generate a SINGLE unified commit message that describes the overall feature or change.
    All these files are part of the same feature/change and should be described together.
    Use Git commit standards and conventions for commit messages: <type>[optional scope]: <description>.
    Return ONLY the commit message text, with no JSON structure, no code blocks, no extra explanation.
    """

client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

###### generator logger ######
ezcommit_logger = getLogger("ezcommit-generator")
ezcommit_logger.setLevel("INFO")
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, "ezcommit-generator.log")
ezcommit_logger.addHandler(FileHandler(log_file, mode='w'))

# Set the log format
log_format = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ezcommit_logger.handlers[0].setFormatter(log_format)
###### generator logger ######

def get_staged_files(repo: git.Repo):
    if repo.bare:
        ezcommit_logger.error("The provided path is not a valid Git repository.")
        raise ValueError("The provided path is not a valid Git repository.")
    
    staged_files = repo.git.diff('--name-only', '--staged').split('\n')
    renamed_files = repo.git.diff('--name-only', '--staged', '--diff-filter=R').split('\n')
    removed_files = repo.git.diff('--name-only', '--staged', '--diff-filter=D').split('\n')

    # Filter out empty strings from split results
    staged_files = [f for f in staged_files if f]
    renamed_files = [f for f in renamed_files if f]
    removed_files = [f for f in removed_files if f]

    return staged_files, renamed_files, removed_files

def generate_file_diffs(repo: git.Repo, staged_files: list, renamed_files: list, removed_files: list):
    diffs = {}
    
    try:
        if repo.head.is_valid() and not repo.head.reference.is_valid():  # Check for empty repo
            raise ValueError("Empty repository")
        
        if repo.head.is_valid():
            for file_path in staged_files:
                # Add -- separator to handle deleted files
                diff = repo.git.diff("HEAD", "--", file_path)
                diffs[file_path] = diff
            for file_path in renamed_files:
                diff = repo.git.diff("HEAD", "--", file_path)
                diffs[file_path] = diff
            for file_path in removed_files:
                # Generate proper delete diff
                diff = repo.git.diff("HEAD", "--", file_path)
                diffs[file_path] = diff
        else:  # Initial commit
            for file_path in staged_files + renamed_files + removed_files:
                diff_sample = f"""diff --git a/{file_path} b/{file_path}
new file mode 100644
index 0000000..e69de29
"""
                diffs[file_path] = diff_sample
                
    except (git.exc.InvalidGitRepositoryError, ValueError) as e:
        ezcommit_logger.error(f"Git error: {str(e)}")
        sys.exit(1)
    
    return diffs

def create_input_for_llm(diffs):
    xml_structure = "<diffs>\n"
    for file, diff in diffs.items():
        xml_structure += f"    <file name='{file}'>\n"
        xml_structure += f"        <diff><![CDATA[{diff}]]></diff>\n"
        xml_structure += "    </file>\n"
    xml_structure += "</diffs>"
    return xml_structure

def extract_json_structure(llm_output: str):
    match = re.search(r'```(?:json\s*)?(.*?)```', llm_output, re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()

def generate_commit_message(xml_str: str):
    try:
        model_name = os.getenv("MODEL_NAME", "")
        if not model_name:
            ezcommit_logger.error("MODEL NAME/ID is Missing. export MODEL_NAME=******")
            print("ERROR: MODEL NAME/ID is Missing. export MODEL_NAME=******")
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": get_prompt(xml_str),
                }
            ],
            model=model_name,
            stream=False,
        )
        return extract_json_structure(response.choices[0].message.content)
    except Exception as e:
        ezcommit_logger.error(f"Error in generating commit message: {e}")
        return None

def generate_unified_commit_message(xml_str: str):
    """Generate a single unified commit message for all changes."""
    try:
        model_name = os.getenv("MODEL_NAME", "")
        if not model_name:
            ezcommit_logger.error("MODEL NAME/ID is Missing. export MODEL_NAME=******")
            print("ERROR: MODEL NAME/ID is Missing. export MODEL_NAME=******")
            return None
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": get_unified_prompt(xml_str),
                }
            ],
            model=model_name,
            stream=False,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        ezcommit_logger.error(f"Error in generating unified commit message: {e}")
        return None

def get_json_as_dict(json_str: str):
    try:
        return json.loads(json_str)
    except Exception as e:
        ezcommit_logger.error(f"JSON parsing error: {e}")
        return {}

def commit_staged_files_with_messages(repo: git.Repo, file_commit_dict: dict):
    try:
        for file_path, commit_message in file_commit_dict.items():
            # Commit just this staged file with its message
            repo.git.commit("-m", commit_message, file_path)
            ezcommit_logger.info(f"Committed {file_path} with message: '{commit_message}'")
    except Exception as e:
        ezcommit_logger.error(f"Error committing: {e}")

def commit_all_staged_files_unified(repo: git.Repo, commit_message: str):
    """Commit all staged files together with a single unified message."""
    try:
        repo.git.commit("-m", commit_message)
        ezcommit_logger.info(f"Committed all staged files with unified message: '{commit_message}'")
        print(f"✓ Committed all staged files with message: '{commit_message}'")
    except Exception as e:
        ezcommit_logger.error(f"Error committing: {e}")
        print(f"ERROR: Failed to commit: {e}")

def ezcommit(repo_path=".", unified=False):
    try:
        if not os.getenv("GROQ_API_KEY"):
            ezcommit_logger.error("API KEY ENV var is Missing. export GROQ_API_KEY=******")
            raise ValueError("API KEY ENV var is Missing. export GROQ_API_KEY=******")
    except Exception as e:
        print("ERROR: API KEY ENV var is Missing. export GROQ_API_KEY=*******")
        return
    
    try:
        repo = git.Repo(repo_path)
        staged_files, renamed_files, removed_files = get_staged_files(repo)
        ezcommit_logger.info(f"Staged files: {staged_files}")
        ezcommit_logger.info(f"Renamed files: {renamed_files}")
        ezcommit_logger.info(f"Removed files: {removed_files}")
        
        diffs = generate_file_diffs(repo, staged_files, renamed_files, removed_files)
        xml_input = create_input_for_llm(diffs)
        
        if unified:
            # Unified mode: generate a single commit message for all files
            ezcommit_logger.info("Using unified commit mode")
            unified_message = generate_unified_commit_message(xml_input)
            if not unified_message:
                ezcommit_logger.error("Failed to generate unified commit message")
                return
            
            ezcommit_logger.info(f"Unified commit message: {unified_message}")
            commit_all_staged_files_unified(repo, unified_message)
        else:
            # Individual mode: generate separate commit messages for each file
            ezcommit_logger.info("Using individual commit mode")
            json_message = generate_commit_message(xml_input)
            if not json_message:
                ezcommit_logger.error("Failed to generate valid commit messages")
                return
            
            file_commit_dict = get_json_as_dict(json_message)
            if not file_commit_dict:
                ezcommit_logger.error("Empty commit dictionary")
                return
                
            ezcommit_logger.info(f"File commit dictionary: {file_commit_dict}")
            commit_staged_files_with_messages(repo, file_commit_dict)
        
    except Exception as e:
        ezcommit_logger.error(f"Error in ezcommit process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ezcommit(".")
    sys.exit(0)