Auto-generate [Jupyter kernels](https://docs.jupyter.org/en/stable/projects/kernels.html) from project directories. Loosely inspired by [repo2docker](https://github.com/jupyterhub/repo2docker/).

# Description

The purpose of this is project is to provide a simple CLI tool that provides a unified interface for three related tasks:

1. Fetch code projects from a variety of repositories (including scientific data repositories).
2. Analyze the fetched project and determine:
  * What dependency ecosystem (`pypi`, `conda`, `julia`...) it uses.
  * What version of the detected language interpreter is used.
3. Create a [Juypyter kernel](https://docs.jupyter.org/en/stable/projects/kernels.html) for the project

# Usage

`python3 main.py --help`
