from .base import Project
from pathlib import Path
import re
import yaml
import os

EMPTY_CONDA_ENV = Path(os.path.dirname(os.path.realpath(__file__))) / ".." / "environment.yml"

# pattern for parsing conda dependency line
PYTHON_VERSION_REGEX = re.compile(r"python\s*[=<>]+\s*([\d\.]*)")
R_VERSION_REGEX = re.compile(r"r-base\s*[=<>]+\s*([\d\.]*)")


class CondaProject(Project):

    project_type = "conda"
    dependencies = ["conda"]

    @classmethod
    def conda_version(self, pkg, version):
        if version:
            if self.is_normal_version(version):
                return f"{pkg}=={version}"
            else:
                return f"{pkg}{version}"
        else:
            return pkg

    def __init__(self, project_path, env_base_path, log, force_init=False, **kwargs):
        super().__init__(project_path, env_base_path, log, **kwargs)
        self._environment_yaml = None
        self._env_file_dependencies = None
        self.env_file = self.binder_path("environment.yml")
        self.detected = CondaProject.detect(self)
        if self.detected or force_init:
            self.base_cmd = ["conda", "run", "-p", str(self.env_path)]
        if force_init:
            CondaProject.create_environment(self)

    @property
    def conda_env_initialized(self):
        return self.env_type == "conda" and self.env_path.exists()

    # This method was adapted from https://github.com/jupyterhub/repo2docker
    # Repo2docker is licensed under the BSD-3 license:
    # https://github.com/jupyterhub/repo2docker/blob/main/LICENSE
    # Copyright (c) 2017, Project Jupyter Contributors
    # All rights reserved.
    @property
    def environment_yaml(self):
        if not self.env_file.exists():
            return {}
        elif self._environment_yaml is None:
            with open(str(self.env_file)) as f:
                env = yaml.safe_load(f) or {}
                self._environment_yaml = env
                return self._environment_yaml
        else:
            return self._environment_yaml

    def env_file_dependencies(self):
        if not self._env_file_dependencies:
            self._env_file_dependencies = self.environment_yaml.get("dependencies", [])
        for dep in self._env_file_dependencies:
            yield dep

    # This method was modified from https://github.com/jupyterhub/repo2docker
    # Repo2docker is licensed under the BSD-3 license:
    # https://github.com/jupyterhub/repo2docker/blob/main/LICENSE
    # Copyright (c) 2017, Project Jupyter Contributors
    # All rights reserved.
    @property
    def uses_r(self):
        """Detect whether the project uses R.

        Will return True when a package prefixed with 'r-' is contained in environment.yml
        """
        if not hasattr(self, "_uses_r"):
            self._uses_r = False
            for dep in self.env_file_dependencies():
                if isinstance(dep, str) and dep.startswith("r-"):
                    self._uses_r = True
                    break
        return self._uses_r

    def conda_install(self, pkg):
        try:
            return self.run([["conda", "install", "-p", str(self.env_path), pkg, "-y"]], {})
        except RuntimeError:
            return False

    # Decorator fur use in subclasses
    def conda_install_dependencies(func, *args, **kwargs):
        def decorate(self, *args, **kwargs):
            if self.conda_env_initialized: # conda env exists
                for dep in self.missing_dependencies():
                    self.log.info(f"Missing dependency '{dep}', attempting to install it using conda...")
                    result = self.conda_install(d)
                    if not result:
                        raise RuntimeError(f"Fatal error: could not conda install dependency '{dep}'.")
            return func(self, *args, **kwargs)
        return decorate

    @Project.check_dependencies
    def create_environment(self, **kwargs):
        if self.conda_env_initialized:
            return True
        elif self.dry_run:
            self.log.info("Dry run enabled. If previous commands were supposed to create a conda env, they haven't. In that case, you may see another attempt to create a conda env.")

        cmd = ["conda", "env", "create", "-f",]
        if self.detected:
            cmd.append(str(self.binder_path("environment.yml")))
        else:
            cmd.append(str(EMPTY_CONDA_ENV))
        cmd.extend(["-p", str(self.env_path)])
        result = self.run([cmd], {})
        return result

    @Project.check_dependencies
    def create_kernel(self, user=False, name="", display_name="", prefix=""):
        return True

    @property
    def python_version(self):
        """Detect whether a python version is declared in environment.yml
        """
        for dep in self.env_file_dependencies():         
            if isinstance(dep, str) and PYTHON_VERSION_REGEX.match(dep):
                return True
                break

    @property
    def r_version(self):
        """Detect whether an R version is declared in environment.yml
        """
        for dep in self.env_file_dependencies():
            if isinstance(dep, str) and R_VERSION_REGEX.match(dep):
                return True
                break

    def detect(self):
        """Check if current repo contains a Conda project."""
        return self.env_file.exists()


    def interpreter_version(self):
        return "not applicable"
