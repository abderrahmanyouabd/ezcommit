import pytest
from unittest.mock import Mock, patch, MagicMock
import git
import os
from ezcommit.commit_generator import (
    get_prompt,
    get_unified_prompt,
    get_staged_files,
    generate_file_diffs,
    create_input_for_llm,
    extract_json_structure,
    generate_commit_message,
    generate_unified_commit_message,
    get_json_as_dict,
    commit_staged_files_with_messages,
    commit_all_staged_files_unified,
    ezcommit
)

@pytest.fixture
def mock_repo():
    repo = Mock(spec=git.Repo)
    repo.bare = False
    repo.git = Mock()
    repo.head.is_valid.return_value = True
    repo.head.reference.is_valid.return_value = True
    return repo

def test_get_prompt():
    xml_str = "<test>data</test>"
    result = get_prompt(xml_str)
    assert isinstance(result, str)
    assert xml_str in result
    assert "```xml" in result
    assert "```json" in result

def test_get_staged_files(mock_repo):
    mock_repo.git.diff.side_effect = [
        "file1.py\nfile2.py",  # staged files
        "",                     # renamed files
        ""                      # removed files
    ]
    
    staged, renamed, removed = get_staged_files(mock_repo)
    assert staged == ["file1.py", "file2.py"]
    assert renamed == []
    assert removed == []

def test_get_staged_files_with_bare_repo():
    mock_repo = Mock(spec=git.Repo)
    mock_repo.bare = True
    
    with pytest.raises(ValueError, match="The provided path is not a valid Git repository"):
        get_staged_files(mock_repo)

def test_generate_file_diffs(mock_repo):
    staged_files = ["file1.py"]
    renamed_files = []
    removed_files = []
    
    mock_repo.git.diff.return_value = "mock diff content"
    
    diffs = generate_file_diffs(mock_repo, staged_files, renamed_files, removed_files)
    assert "file1.py" in diffs
    assert diffs["file1.py"] == "mock diff content"

def test_create_input_for_llm():
    diffs = {
        "file1.py": "diff content 1",
        "file2.py": "diff content 2"
    }
    
    xml_str = create_input_for_llm(diffs)
    assert "<diffs>" in xml_str
    assert "<file name='file1.py'>" in xml_str
    assert "<file name='file2.py'>" in xml_str
    assert "diff content 1" in xml_str
    assert "diff content 2" in xml_str

def test_extract_json_structure():
    test_input = "some text\n```json\n{\"key\": \"value\"}\n```\nmore text"
    result = extract_json_structure(test_input)
    assert result == '{\"key\": \"value\"}'

    # Test with no JSON
    assert extract_json_structure("no json here") is None

def test_get_json_as_dict():
    # Valid JSON
    valid_json = '{"file1.py": "feat: add new feature"}'
    result = get_json_as_dict(valid_json)
    assert isinstance(result, dict)
    assert result["file1.py"] == "feat: add new feature"

    # Invalid JSON
    invalid_json = 'invalid json'
    result = get_json_as_dict(invalid_json)
    assert result == {}

@patch('ezcommit.commit_generator.client')
def test_generate_commit_message(mock_client):
    # Mock the Groq client response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '```json\n{"file1.py": "feat: test"}\n```'
    mock_client.chat.completions.create.return_value = mock_response

    # Set environment variable
    os.environ["MODEL_NAME"] = "test-model"
    
    result = generate_commit_message("<test>xml</test>")
    assert result == '{"file1.py": "feat: test"}'

def test_commit_staged_files_with_messages(mock_repo):
    file_commit_dict = {
        "file1.py": "feat: add feature",
        "file2.py": "fix: bug fix"
    }
    
    commit_staged_files_with_messages(mock_repo, file_commit_dict)
    
    # Verify commits were made
    assert mock_repo.git.commit.call_count == 2
    mock_repo.git.commit.assert_any_call("-m", "feat: add feature", "file1.py")
    mock_repo.git.commit.assert_any_call("-m", "fix: bug fix", "file2.py")

@patch('ezcommit.commit_generator.git.Repo')
@patch('ezcommit.commit_generator.generate_commit_message')
def test_ezcommit(mock_generate_commit, mock_repo_class):
    # Setup environment
    os.environ["GROQ_API_KEY"] = "test-key"
    os.environ["MODEL_NAME"] = "test-model"  # Add MODEL_NAME env var
    
    # Mock repository
    mock_repo = Mock()
    mock_repo_class.return_value = mock_repo
    # Set bare=False to avoid ValueError
    mock_repo.bare = False
    
    # Mock all the different git diff calls
    mock_repo.git.diff.side_effect = [
        "file1.py",  # for get_staged_files
        "",          # for renamed files
        "",          # for removed files
        "diff --git a/file1.py b/file1.py\n+some changes"  # for generate_file_diffs
    ]
    
    mock_repo.head.is_valid.return_value = True
    mock_repo.head.reference.is_valid.return_value = True
    
    # Mock commit message generation
    mock_generate_commit.return_value = '{"file1.py": "feat: test commit"}'
    
    # Run ezcommit
    with patch('sys.exit') as mock_exit:  # Prevent actual system exit
        ezcommit(".")
        mock_exit.assert_not_called()  # Should not exit if everything works
    
    # Verify the commit was attempted
    mock_repo.git.commit.assert_called_once()

def test_ezcommit_missing_api_key():
    # Remove API key from environment
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]
    
    # The function should return early when API key is missing
    result = ezcommit(".")
    assert result is None  # Function returns None when API key is missing

def test_get_unified_prompt():
    xml_str = "<test>data</test>"
    result = get_unified_prompt(xml_str)
    assert isinstance(result, str)
    assert xml_str in result
    assert "SINGLE unified commit message" in result
    assert "```xml" in result

@patch('ezcommit.commit_generator.client')
def test_generate_unified_commit_message(mock_client):
    # Mock the Groq client response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = 'feat: implement user authentication system'
    mock_client.chat.completions.create.return_value = mock_response

    # Set environment variable
    os.environ["MODEL_NAME"] = "test-model"
    
    result = generate_unified_commit_message("<test>xml</test>")
    assert result == 'feat: implement user authentication system'

def test_commit_all_staged_files_unified(mock_repo):
    commit_message = "feat: implement new feature across multiple files"
    
    commit_all_staged_files_unified(mock_repo, commit_message)
    
    # Verify single commit was made with all staged files
    mock_repo.git.commit.assert_called_once_with("-m", commit_message)

@patch('ezcommit.commit_generator.git.Repo')
@patch('ezcommit.commit_generator.generate_unified_commit_message')
def test_ezcommit_unified_mode(mock_generate_unified, mock_repo_class):
    # Setup environment
    os.environ["GROQ_API_KEY"] = "test-key"
    os.environ["MODEL_NAME"] = "test-model"
    
    # Mock repository
    mock_repo = Mock()
    mock_repo_class.return_value = mock_repo
    mock_repo.bare = False
    
    # Mock all the different git diff calls
    mock_repo.git.diff.side_effect = [
        "file1.py\nfile2.py",  # for get_staged_files
        "",                     # for renamed files
        "",                     # for removed files
        "diff --git a/file1.py b/file1.py\n+some changes",  # for generate_file_diffs file1
        "diff --git a/file2.py b/file2.py\n+more changes"   # for generate_file_diffs file2
    ]
    
    mock_repo.head.is_valid.return_value = True
    mock_repo.head.reference.is_valid.return_value = True
    
    # Mock unified commit message generation
    mock_generate_unified.return_value = 'feat: implement authentication system'
    
    # Run ezcommit with unified mode
    with patch('sys.exit') as mock_exit:
        ezcommit(".", unified=True)
        mock_exit.assert_not_called()
    
    # Verify the unified commit was made
    mock_repo.git.commit.assert_called_once_with("-m", 'feat: implement authentication system')

