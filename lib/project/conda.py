from .python import PythonProject
from .r import RProject
from .base import Project
from pathlib import Path
import re
import yaml

# pattern for parsing conda dependency line
PYTHON_REGEX = re.compile(r"python\s*=+\s*([\d\.]*)")

class CondaProject(PythonProject, RProject):

    name = "Conda"
    dependencies = ["conda"]

    def __init__(self, project_path, env_path, log, **kwargs):
        PythonProject.__init__(self, project_path, env_path, log, **kwargs)
        RProject.__init__(self, project_path, env_path, log, **kwargs)
        self._environment_yaml = None
        self._env_file_dependencies = None
        self.detect()
        self.base_cmd = ["conda", "run", "-p", str(self.env_path)]

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
            with open(self.dependency_files["environment.yml"]) as f:
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

    @property
    def uses_python(self):
        """Detect whether a python version is declared in environment.yml
        """
        if not hasattr(self, "_uses_python"):
            self._uses_python = False
            for dep in self.env_file_dependencies():
                if isinstance(dep, dict) and dep.get('pip', False):
                    self._uses_python = True
                    break                
                if isinstance(dep, str) and PYTHON_REGEX.match(dep):
                    self._uses_python = True
                    break
        return self._uses_python

    def cmd_init_environment(self):
        cmds = [
            ["conda", "env", "create", "-f", str(self.binder_path("environment.yml")), "-p", str(self.env_path)]
        ]
        return (cmds, {})

    @Project.sanity_check
    def create_environment(self, **kwargs):
        dry_run = kwargs.get('dry_run', False)
        def conda_install(pkg):
            self.run([["conda", "install", "-p", str(self.env_path), pkg, "-y"]], {}, dry_run=dry_run)

        dry_run = kwargs.get('dry_run', False)

        self.run(*self.cmd_init_environment(), dry_run=dry_run)

        cmds = []

        for project_type in self.detected_languages:
            if project_type is not self.__class__:
                for dep in project_type.missing_dependencies(self):
                    conda_install(dep)
                if (project_type is PythonProject) and (v := self.python_version):
                   conda_install(v)
                project_type.create_environment(self, base_cmd=self.base_cmd, dry_run=dry_run)

        # optional: conda clean --all -f -y

        self.run(cmds, {}, dry_run=dry_run)
        return True

    @Project.sanity_check
    def create_kernel(self, user=False, name="", display_name="", prefix="", dry_run=False):
        if not (dry_run or self.uses_python or self.uses_r):
            raise RuntimeError(f"Aborting: could not find either R or Python in conda environment in {env_path}. Do not know how to create Jupyter kernel.")

        _name = name or self.env_name
        
        for project_type in self.detected_languages:
            if project_type is not self.__class__:
                project_type.create_kernel(self, user=user, name=f"{project_type.name}-{_name}", display_name=display_name, prefix=prefix, base_cmd=self.base_cmd, dry_run=dry_run)

        return True

    def is_normal_version(self, v):
        test = r"!<>=,"
        return not any(x in test for x in v)

    @property
    def python_version(self):
        if PythonProject in self.detected_languages and not self.uses_python:
            v = super().python_version
            if self.is_normal_version(v):
                return f"python=={v}"
            else:
                return f"python{v}"
            return 
        return None

    @Project.wrap_detect
    def detect(self):
        """Check if current repo contains a Conda project."""
        env_yml = self.binder_path("environment.yml")
        if env_yml.exists():
            self.dependency_files["environment.yml"] = str(env_yml)
            if self.uses_r:
                self.detected_languages.add(RProject)
            if self.uses_python:
                self.detected_languages.add(PythonProject)
            return CondaProject
        return False
