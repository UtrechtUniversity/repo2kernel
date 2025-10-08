Auto-generate [Jupyter kernels](https://docs.jupyter.org/en/stable/projects/kernels.html) from project directories. Loosely inspired by [repo2docker](https://github.com/jupyterhub/repo2docker/).

# Description

The purpose of this is project is to provide a simple CLI tool that provides a unified interface for three related tasks:

1. Fetch code projects from a variety of repositories (including scientific data repositories).
2. Analyze the fetched project and determine:
    * What dependency ecosystem (`pypi`, `conda`, `julia`...) it uses.
    * What version of the detected language interpreter is used.
3. Create a [Juypyter kernel](https://docs.jupyter.org/en/stable/projects/kernels.html) for the project

`repo2kernel` is built on top of `repo2docker`, which powers Binder. This means any Binder project that contains any of the [supported project](#supported-projects) types should also work with `repo2kernel`!

## Supported projects

The following kinds of projects are currently supported:

1. Python projects, with any of the following dependency files:
  * `pyproject.toml` (also for specifying the Python version)
  * `setup.py`
  * `Pipfile` or `Pipfile.lock`
  * `requirements.txt`
  * `runtime.txt` (for specifying the Python version, see [repo2docker](https://repo2docker.readthedocs.io/en/latest/howto/languages/#specify-a-version-of-python))
2. R projects, with any of the following dependency files:
  * `DESCRIPTION`
  * `install.R` (see [repo2docker](https://repo2docker.readthedocs.io/en/latest/howto/languages/#the-r-language))
  * `runtime.txt` (for specifying the R version, see [repo2docker](https://repo2docker.readthedocs.io/en/latest/howto/languages/#the-r-language))
3. Julia projects, with `Project.toml`
4. `conda` projects, with `environment.yml`
  * if an `environment.yml` is detected in the project, then any additional R and Python dependencies (as described above) will be installed into the created conda environment.

## Dependencies

* `uv` to resolve Python
* `conda` to resolve R projects and `conda` projects
* `juliaup` to resolve Julia projects

These tools must be available on `PATH` when executing `repo2kernel`.

# Usage

You can install this project locally, or use `uvx` to run it directly from github (prerequisite: install [uv](github.com/astral-sh/uv/)).

## Fetch a project from online

Like [Binder](https://github.com/jupyterhub/mybinder.org-user-guide), `repo2kernel` supports fetching URLs (e.g. to a git repo), and even DOIs:

`uvx git+https://github.com/UtrechtUniversity/repo2kernel fetch doi:10.7910/DVN/6ZXAGT/3YRRYJ /where/to/download`

## Create a kernel from a directory

`uvx git+https://github.com/UtrechtUniversity/repo2kernel create /path/to/my/downloaded/project --base-env-dir /tmp/path/to/envs --env-name testproject`

Then, when starting Jupyter, you should see kernels named `"testproject"` for each detected language (e.g. `Python Kernel testproject`).

## Creating an 'empty' kernel for a language

If you want to create a kernel for a specific language and version without installing any additional dependencies, use the `new` command:

`uvx git+https://github.com/UtrechtUniversity/repo2kernel new julia --version 1.11.7 --base-env-dir /tmp/path/to/envs`
