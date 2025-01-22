# EffortZeroCommit

Automated Git commit message generator using AI.

## Installation

```bash
pip install ezcommit
```

## Usage

1. Stage your files:
```bash
git add .
```

2. Generate commit messages and commit:
```bash
ezcommit -run
```

## Configuration

Create a `.env` file with your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=mixtral-8x7b-32768
```

## License

MIT License