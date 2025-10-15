from repo2docker.buildpacks import BaseImage

from pathlib import Path
from shutil import which
import subprocess
import os
import tempfile
import uuid

class Project(BaseImage):

    project_type = "project"
    kernel_base_display_name = "Kernel"
    dependencies = []
    default_version=""

    @classmethod
    def add_to_path(self, *args):
        return os.pathsep.join([*args, os.environ.get("PATH", "")])

    @classmethod
    def dict2cli(self, opts):
        return [f"--{k.replace('_', '-')}{f'={v}'}" for k,v in opts.items() if v]

    @classmethod
    def is_normal_version(self, v):
        if not v:
            return False
        test = r"!<>=,"
        return not any(x in test for x in v)

    def __init__(self, project_path, env_base_path, log, base_cmd = [], interpreter_version="", env_type=None, env_name="", force_init=False, dry_run=False, conda_install_deps=False, **kwargs):
        self.force_init = force_init
        self.dry_run = dry_run
        self.log = log
        self.base_cmd = []
        self.detected = False
        self.conda_install_deps = conda_install_deps

        self.env_base_path = Path(env_base_path)
        self.env_type = env_type or self.__class__.project_type

        if project_path:
            self._interpreter_version = ""
            self.project_path = Path(project_path)
            self._env_name = env_name or self.project_path.stem
        elif self.force_init:
            # we have no project dir, but will force the creation of a new environment
            self._tmp_dir = tempfile.TemporaryDirectory()
            self.project_path =  Path(self._tmp_dir.name) # mock a project directory that is empty, so no dependency files will be detected
            self._interpreter_version = interpreter_version or self.default_version
            if env_name:
                self._env_name = env_name
            elif self.is_normal_version(self._interpreter_version):
                self._env_name = f"v{self._interpreter_version}"
            else:
                self._env_name = uuid.uuid4().hex
        else:
            raise ValueError("Either project_path must be set, or force_init must be True.")

        self.env_path = self.env_base_path / self.env_type / self.env_name


    def __del__(self):
        if getattr(self, '_tmp_dir', False):
            self.log.debug(f"Cleaning up temporary directory {self._tmp_dir}")
            self._tmp_dir.cleanup()

    @property
    def env_name(self):
        # TODO: normalize?
        return f"{self._env_name}"

    def kernel_display_name(self, name):
        return f"{self.kernel_base_display_name} {name or self.env_name}"

    def missing_dependencies(self, path=os.environ.get("PATH", ""), dependencies=[]):
        return [d for d in (dependencies or self.dependencies) if not which(d, path=path)]

    def check_dependencies(func, *args, **kwargs):
        def decorate(self, *args, **kwargs):
            missing = self.missing_dependencies()
            if len(missing) > 0:
                raise RuntimeError(f"Missing dependencies: {missing}")
            return func(self, *args, **kwargs)
        return decorate

    def check_detected(func, *args, **kwargs):
        def decorate(self, *args, **kwargs):
            if not self.detected and not self.force_init:
               self.log.warning(f"No {self.env_type} environment detected in {self.project_path}")
               return False
            else:
                return func(self, *args, **kwargs)
        return decorate

    def create_environment(self, interpreter_base_dir=""):
        return True

    def create_kernel(self, user=False, name="", display_name="", prefix=""):
        return True

    def detect(self):
        return True

    @property
    def binder_dir(self):
        binder_path = self.project_path / "binder"
        dotbinder_path = self.project_path / ".binder"

        has_binder = binder_path.is_dir()
        has_dotbinder = dotbinder_path.is_dir()

        if has_binder and has_dotbinder:
            raise RuntimeError(
                "The repository contains both a 'binder' and a '.binder' "
                "directory. However they are exclusive."
            )

        if has_dotbinder:
            return dotbinder_path
        elif has_binder:
            return binder_path
        else:
            return self.project_path

    def binder_path(self, path):
        """Locate a file"""
        return self.binder_dir / path

    def run(self, commands, env):
        self.log.info("Will run the following commands:")
        for cmd in commands:
            self.log.info(cmd)
        if len(env.keys()) > 0:
            self.log.info("...with the following environment variables:")
            self.log.info(env)
        if not self.dry_run:
            for cmd in commands:
                p = subprocess.Popen(cmd, env=(os.environ.copy() | env), shell=isinstance(cmd, str), cwd=self.project_path)
                exit_code = p.wait()
                if exit_code > 0:
                    raise RuntimeError(f"Error! repo2kernel is aborting after the following command failed:\n{cmd}")
                else:
                    self.log.info("...success")
        return True

    @property
    def interpreter_version(self):
        return self._interpreter_version
