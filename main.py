import repo2docker.contentproviders
from lib import PythonProject, CondaProject, RCondaProject

import argparse

SUCCESS = 0
NOTHING_FOUND = 2
CREATION_FAILED = 3

PROJECT_TYPES = [
    CondaProject,
    PythonProject,
    RCondaProject,
]

CONTENT_PROVIDERS = {
    repo2docker.contentproviders.Local,
    repo2docker.contentproviders.Zenodo,
    repo2docker.contentproviders.Dataverse,
    repo2docker.contentproviders.Mercurial,
    repo2docker.contentproviders.Git,
}

def get_argparser():
    parser = argparse.ArgumentParser(
        prog='repo2kernel',
        description='Create a Jupyter kernel from the dependencies found in a directory. Supports multiple environment managers and languages.',
    )

    subparsers = parser.add_subparsers(dest="subparser_name", help='sub-command help')

    fetch_parser = subparsers.add_parser('fetch', help='fetch a project from an online datasource')
    detect_parser = subparsers.add_parser('detect', help='detect a directory for depedencies and output results')
    create_parser = subparsers.add_parser('create', help='create kernel for a directory')

    fetch_parser.add_argument('url', help='URL to fetch. This program supports XYZ kinds of URLs')
    fetch_parser.add_argument('target', help='Where the downloaded project will be saved')
    fetch_parser.add_argument('--ref', help='Version of the project to be fetched (e.g. a git tag)')

    detect_parser.add_argument('directory', help='Project to detect')

    create_parser.add_argument('directory', help='Project to create kernel for')
    create_parser.add_argument('--dry-run', action='store_true', help='if enabled, will only print the commands to be run, not actually execute them')
    create_parser.add_argument('--virtual-env-dir', required=True, help='path where the newly created environment for the project wil be saved')
    create_parser.add_argument('--interpreter-base-dir', help='base path where newly fetched versions of the interpreter used in the project will be saved')
    create_parser.add_argument('--kernel-user', action='store_true', help='whether to install the kernel only for the current user')
    create_parser.add_argument('--kernel-prefix', help='path prefix for kernel install location')
    create_parser.add_argument('--kernel-name', help='name of the kernel')
    create_parser.add_argument('--kernel-display-name', help='display name of the kernel')

    return parser

class CliCommands():
    
    import logging

    log = logging.getLogger("repo2kernel")
    logging.basicConfig(level=logging.INFO)

    @classmethod
    # This method was adapted from https://github.com/jupyterhub/repo2docker
    # Repo2docker is licensed under the BSD-3 license:
    # https://github.com/jupyterhub/repo2docker/blob/main/LICENSE
    # Copyright (c) 2017, Project Jupyter Contributors
    # All rights reserved.
    def fetch(self, url="", target="", ref=""):
        """Fetch the contents of `url` and place it in `target`.

        The `ref` parameter specifies what "version" of the contents should be
        fetched. In the case of a git repository `ref` is the SHA-1 of a commit.

        Iterate through possible content providers until a valid provider,
        based on URL, is found.
        """
        picked_content_provider = None
        for ContentProvider in CONTENT_PROVIDERS:
            cp = ContentProvider()
            spec = cp.detect(url, ref=ref)
            if spec is not None:
                picked_content_provider = cp
                self.log.info(f"Picked {cp.__class__.__name__} content provider.\n")
                break
        
        if picked_content_provider is None:
            self.log.error(f"No matching content provider found for {url}.")

        for log_line in picked_content_provider.fetch(
            spec, target, yield_output=False
        ):
            self.log.info(log_line)


    @classmethod
    def detect(self, directory=""):
        found = False
        for project_cls in PROJECT_TYPES:
            project = project_cls(directory, "", self.log, dry_run=True)

            if not project.detected:
                continue
            
            found = True

            print(f"Discovered project in {directory}")
                
            print(f"Found dependency files in: {project.binder_dir}")
            print(f"Interpreter: {project.project_type}")
            print(f"Version: {project.interpreter_version() or 'not defined'}")
        if not found:
            print(f"No projects found in {directory}!")
            return NOTHING_FOUND
        return SUCCESS

    @classmethod
    def create(self, directory="", dry_run=False, virtual_env_dir="", interpreter_base_dir="", kernel_user=False, kernel_prefix="", kernel_name="", kernel_display_name=""):
        env_prefix = None
        try:            
            for project_cls in PROJECT_TYPES:
                project = project_cls(directory, virtual_env_dir, self.log, env_prefix=env_prefix, dry_run=dry_run)
                if project.detected:
                    project.create_environment(interpreter_base_dir=interpreter_base_dir)
                    project.create_kernel(user=kernel_user, name=kernel_name, display_name=kernel_display_name, prefix=kernel_prefix)
                    if type(project) == CondaProject:
                        env_prefix = "conda"
        except RuntimeError as e:
            self.log.warning(e)
            return CREATION_FAILED
        return SUCCESS
        

if __name__ == "__main__":
    args = get_argparser().parse_args()
    command = getattr(CliCommands, args.subparser_name)
    opts = vars(args)
    del opts['subparser_name']
    code = command(**opts)
    exit(code)
