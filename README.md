# EffortZeroCommit

Automated Git commit message generator using AI.

## Dependencies

- Git must be installed on your system. You can download it from [git-scm.com](https://git-scm.com/)

## Installation

```bash
pip install effort-zero-commit
```

## Usage

1. Stage your desired files:
```bash
git add .
```

2. Generate commit messages and commit:
```bash
ezcommit -run
```

## Configuration

Using your terminal, export your Groq API key and model name:
```env
# Windows (Command Prompt):
set GROQ_API_KEY=your_groq_api_key_here
set MODEL_NAME=mixtral-8x7b-32768

# Windows (PowerShell):
$env:GROQ_API_KEY="your_groq_api_key_here"
$env:MODEL_NAME="mixtral-8x7b-32768"

# Linux/macOS:
export GROQ_API_KEY=your_groq_api_key_here
export MODEL_NAME=mixtral-8x7b-32768
```

## License

[MIT License](LICENSE)