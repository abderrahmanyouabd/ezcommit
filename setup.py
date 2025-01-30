from setuptools import setup, find_packages

# Read the contents of README file
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="effort-zero-commit",
    version="0.1.3",
    author="Abderrahman Youabd",
    author_email="youabd50@gmail.com",
    description="Automated Git commit message generator using AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abderrahmanyouabd/ezcommit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.9",
    install_requires=[
        "gitpython",
        "groq",
        "python-dotenv",
        "click",
        "json-with-comments"
    ],
    entry_points={
        'console_scripts': [
            'ezcommit=ezcommit.cli:main',
        ],
    },
)