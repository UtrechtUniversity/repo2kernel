import repo2docker.contentproviders
from lib import PythonProject
import subprocess, os

import argparse

PROJECT_TYPES = {
    PythonProject
}

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

    @classmethod
    def _run(self, commands, env, dry_run=False):
        print("Will run the following commands: ")
        print(commands)
        for cmd in commands:
            print(cmd)
        print("...with the following environment variables:")
        print(env)
        if not dry_run:
            for cmd in commands:
                print(f"Running: {cmd}")
                p = subprocess.Popen(cmd, env=(os.environ.copy() | env), shell=isinstance(cmd, str))
                exit_code = p.wait()
                if exit_code > 0:
                    raise RuntimeError(f"Error! repo2kernel is aborting after the following command failed:\n{cmd}")
                else:
                    print("...success")

    @classmethod
    def _detect(self, directory):
        detected_project_types = []
        for project_class in PROJECT_TYPES:
            project = project_class(directory)
            if project.detected:
                detected_project_types.append(project) 
        return detected_project_types

    @classmethod
    # This method was adapted from https://github.com/jupyterhub/repo2docker
    # See here for the original license (BSD-3):
    # https://github.com/jupyterhub/repo2docker/blob/main/LICENSE
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
        detected_project_types = self._detect(directory)
        for project in detected_project_types:
            print(f"Discovered project: {project.name} {project.version}")

    @classmethod
    def create(self, directory="", dry_run=False, virtual_env_dir="", interpreter_base_dir="", kernel_user=False, kernel_prefix="", kernel_name="", kernel_display_name=""):
        detected_project_types = self._detect(directory)
        for project in detected_project_types:
            print(f"Discovered project: {project.name} {project.version}")
            print(f"Running commands to create environment in {virtual_env_dir}")
            self._run(*project.install_commands(virtual_env_dir, interpreter_base_dir=interpreter_base_dir), dry_run=dry_run)
            print(f"Running commands to create kernel:")
            self._run(*project.install_kernel_commands(virtual_env_dir, user=kernel_user, name=kernel_name, display_name=kernel_display_name, prefix=kernel_prefix), dry_run=dry_run)

if __name__ == "__main__":
    args = get_argparser().parse_args()
    command = getattr(CliCommands, args.subparser_name)
    opts = vars(args)
    del opts['subparser_name']
    command(**opts)
