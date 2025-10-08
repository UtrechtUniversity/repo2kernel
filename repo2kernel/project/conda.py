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
        super().__init__(project_path, env_base_path, log, force_init=force_init, **kwargs)
        self._environment_yaml = None
        self._env_file_dependencies = None
        self.env_file = self.binder_path("environment.yml")
        self.detected = CondaProject.detect(self)
        if self.detected or (force_init and self.env_type == "conda"):
            self.conda_path = self.env_path
            self.base_cmd = ["conda", "run", "-p", str(self.conda_path)]

    @property
    def conda_env_initialized(self):
        return self.env_type == "conda" and self.conda_path.exists()

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

    def conda_install(self, *args):
        return self.run([["conda", "install", "-p", str(self.conda_path), *args, "-y"]], {})

    def missing_dependencies(self):
        if self.conda_env_initialized:
            path = self.__class__.add_to_path(str((self.conda_path / "bin").resolve()))
        else:
            path = os.environ.get("PATH", "")
        return super().missing_dependencies(path=path)

    # Decorator fur use in subclasses
    def conda_install_dependencies(func, *args, **kwargs):
        def decorate(self, *args, **kwargs):
            if self.conda_env_initialized: # conda env exists
                missing = self.missing_dependencies()
                if len(missing) > 0:
                    self.log.info(f"Missing dependencies: {missing}")
                    self.log.info("Attempting to install missing dependencies using conda...")
                    try:
                        self.conda_install(*missing)
                    except RuntimeError as err:
                        self.log.error("Fatal error: could not install dependencies using conda:")
                        raise err
            return func(self, *args, **kwargs)
        return decorate

    @Project.check_detected
    @Project.check_dependencies
    def create_environment(self, **kwargs):
        if self.conda_env_initialized or self.env_type != "conda":
            return True
        elif self.dry_run:
            self.log.info("Dry run enabled, will skip conda env creation and you will not see conda env creation command in the dry run output.")
            return True

        cmd = ["conda", "env", "create", "-f",]
        if self.env_file.exists():
            cmd.append(str(self.env_file))
        else:
            cmd.append(str(EMPTY_CONDA_ENV))
        cmd.extend(["-p", str(self.conda_path)])
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
