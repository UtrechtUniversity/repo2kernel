from .base import Project
from pathlib import Path
import re
import yaml

# pattern for parsing conda dependency line
PYTHON_REGEX = re.compile(r"python\s*[=<>]+\s*([\d\.]*)")
R_BASE_REGEX = re.compile(r"r-base\s*[=<>]+\s*([\d\.]*)")


class CondaProject(Project):

    name = "Conda"
    dependencies = ["conda"]

    def __init__(self, project_path, env_path, log, force_init=False, **kwargs):
        super().__init__(project_path, env_path, log, **kwargs)
        self._environment_yaml = None
        self._env_file_dependencies = None
        self.env_initialized = False
        self.detected = self.detect()
        if self.detected or force_init:
            self.base_cmd = ["conda", "run", "-p", str(self.env_path)]
            CondaProject.create_environment(self)

    # This method was adapted from https://github.com/jupyterhub/repo2docker
    # Repo2docker is licensed under the BSD-3 license:
    # https://github.com/jupyterhub/repo2docker/blob/main/LICENSE
    # Copyright (c) 2017, Project Jupyter Contributors
    # All rights reserved.
    @property
    def environment_yaml(self):
        if not self.detected:
            return {}
        elif self._environment_yaml is None:
            with open(self.binder_path("environment.yml")) as f:
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
        self.run([["conda", "install", "-p", str(self.env_path), pkg, "-y"]], {})

    # Decorator fur use in subclasses
    def conda_install_dependencies(func, *args, **kwargs):
        def decorate(self, *args, **kwargs):
            if self.env_initialized: # conda env exists
                for dep in self.missing_dependencies():
                    self.log.info(f"Missing dependency '{dep}', attempting to install it using conda...")
                    self.conda_install(d)
            return func(self, *args, **kwargs)
        return decorate

    @Project.sanity_check
    def create_environment(self, **kwargs):
        cmd = ["conda", "env", "create"]
        if self.detected:
            cmd.extend(["-f", str(self.binder_path("environment.yml").resolve())])
        cmd.extend(["-p", str(self.env_path)])
        result = self.run([cmd], {})
        if result:
            self.env_initialized = True
        return result

    def create_kernel(self, user=False, name="", display_name="", prefix=""):
        return True

    @property
    def python_version(self):
        """Detect whether a python version is declared in environment.yml
        """
        for dep in self.env_file_dependencies():         
            if isinstance(dep, str) and PYTHON_REGEX.match(dep):
                return True
                break

    @property
    def r_version(self):
        """Detect whether an R version is declared in environment.yml
        """
        for dep in self.env_file_dependencies():
            if isinstance(dep, str) and R_BASE_REGEX.match(dep):
                return True
                break

    def detect(self):
        """Check if current repo contains a Conda project."""
        return self.binder_path("environment.yml").exists()
