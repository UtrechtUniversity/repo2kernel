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
    dependencies = ['conda']
    kernel_package_r = "r-irkernel"

    def __init__(self, path, log, **kwargs):
        super().__init__(path, log, **kwargs)
        self._environment_yaml = None

    @property
    def environment_yaml(self):
        if self._environment_yaml is None:
            with open(self.env_file.resolve()) as f:
                env = yaml.safe_load(f) or {}
                self._environment_yaml = env
                return self._environment_yaml
        elif not self.detected:
            return {}
        else:
            return self._environment_yaml

    @property
    def uses_r(self):
        """Detect whether the project uses R.

        Will return True when a package prefixed with 'r-' is being installed.
        """
        if not hasattr(self, "_uses_r"):
            deps = self.environment_yaml.get("dependencies", [])
            self._uses_r = False
            for dep in deps:
                if not isinstance(dep, str):
                    continue
                if dep.startswith("r-"):
                    self._uses_r = True
                    break
        return self._uses_r


    @property
    def uses_python(self):
        """Detect whether the project uses Python.
        """
        if not hasattr(self, "_uses_python"):
            deps = self.environment_yaml.get("dependencies", [])
            self._uses_python = False
            for dep in deps:
                if isinstance(dep, dict) and dep.get('pip', False):
                    self._uses_python = True
                    break                
                if PYTHON_REGEX.match(dep):
                    self._uses_python = True
                    break
        return self._uses_python

    def create_environment(self, env_create_path, **kwargs):
        Project.create_environment(self, env_create_path, **kwargs)

        dry_run = kwargs.get('dry_run', False)

        cmds =  [
            ["conda", "env", "create", "-f", str(self.binder_path("environment.yml").resolve()), "-p", env_create_path]
        ]

        self.run(cmds, {}, dry_run)
        cmds = []

        if self.uses_r:
            cmds.append(["conda", "install", "-p", env_create_path, self.kernel_package_r, "-y"])
        if self.uses_python:
            cmds.append(["conda", "install", "-p", env_create_path, self.kernel_package_py, "-y"])
            if self.use_requirements_txt:
                cmds.append(["conda", "run", "-p", env_create_path, "pip", "install", "-r", str(self.binder_path("requirements.txt").resolve())])

        # optional: conda clean --all -f -y

        self.run(cmds, {}, dry_run)
        return True


    def create_kernel(self, env_path, user=False, name="", display_name="", prefix="", dry_run=False):
        if not (dry_run or self.uses_python or self.uses_r):
            raise RuntimeError(f"Aborting: could not find either R or Python in conda environment in {env_path}. Do not know how to create Jupyter kernel.")

        _name = name or self.env_name
        _base_cmd = ["conda", "run", "-p", env_path]
        
        if self.uses_python:
            PythonProject.create_kernel(self, env_path, user=user, name=f"python-{_name}", display_name=display_name, prefix=prefix, dry_run=dry_run, base_cmd=_base_cmd)
        if self.uses_r:
            RProject.create_kernel(self, env_path, user=user, name=f"r-{_name}", display_name=display_name, prefix=prefix, dry_run=dry_run, base_cmd=_base_cmd)

        return True

    def detect(self):
        """Check if current repo contains a Conda project."""
        PythonProject.detect(self) # PythonProject.detect() to detect requirements.txt
        self.env_file = self.binder_path("environment.yml")
        return self.env_file.exists()
