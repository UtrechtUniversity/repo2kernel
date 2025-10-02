from .conda import CondaProject
from .base import Project
import tomllib

class PythonProject(CondaProject):

    project_type = "python"
    kernel_base_display_name = "Python Kernel"
    default_python_version="3"
    dependencies = ["uv"]
    kernel_package_py = "ipykernel"

    def __init__(self, project_path, env_base_path, log, **kwargs):
        super().__init__(project_path, env_base_path, log, **kwargs)
        self.dependency_file = ""
        self.detected = self.detect()

    @Project.check_detected
    @CondaProject.conda_install_dependencies
    def create_environment(self, interpreter_base_dir=""):
        if not super().python_version: # python was not installed from environment.yml
            if self.conda_env_initialized: # use conda to install python
                v = self.python_version
                self.conda_install(self.__class__.conda_version("python", v))
            else: # use uv to install python
                env = {}
                if interpreter_base_dir:
                    env["UV_PYTHON_INSTALL_DIR"] = interpreter_base_dir
                cmds = [
                    ["uv", "python", "install", self.python_version],
                    ["uv", "venv", str(self.env_path), "--python", self.python_version]
                ]
                self.run(cmds, env)

        cmds = []
        if self.dependency_file:
            match self.dependency_file.name:
                case "pyproject.toml" | "setup.py":
                    cmds.append([*self.base_cmd, "uv", "pip", "install", str(self.binder_dir)])
                case "Pipfile.lock":
                    cmds.append([*self.base_cmd, "uvx", "pipenv", "install", "--ignore-pipfile --dev"])
                case "Pipfile":
                    cmds.append([*self.base_cmd, "uvx", "pipenv", "install", "--skip-lock", "--dev"])
                case "requirements.txt":
                    cmds.append([*self.base_cmd, "uv", "pip", "install", "-r", str(self.dependency_file)])

        cmds.append([*self.base_cmd, "uv", "pip", "install", self.kernel_package_py])

        self.run(cmds, {"VIRTUAL_ENV": str(self.env_path) })

        return True

    @Project.check_detected
    @CondaProject.conda_install_dependencies
    def create_kernel(self, user=False, name="", display_name="", prefix=""):
        Project.create_kernel(self, self.env_path) # sanity checks

        options = {
            'name': name or self.env_name,
            'display_name': display_name or self.kernel_display_name(),
            'user': user,
            'prefix': prefix
        }

        if self.conda_env_initialized:
            python_cmd = ["python", "-m"]
        else:
            python_cmd = ["uv", "run", "--active", "python", "-m"]

        cmds = [
            [*self.base_cmd, *python_cmd, self.kernel_package_py, "install", *self.__class__.dict2cli(options)]
        ]

        self.run(cmds, { "VIRTUAL_ENV": str(self.env_path) })
        return True

    @property
    def python_version(self):
        if version := super().python_version:
            return version

        runtime_version = self.runtime[1]
        if runtime_version:
            version = runtime_version.rstrip()
        elif (python_version_file := self.project_path / ".python-version") and python_version_file.exists():
            version = python_version_file.read_text().rstrip()
        elif (pyproject := self.project_path / "pyproject.toml") and pyproject.exists():
            with open(pyproject.resolve(), "rb") as f:
                data = tomllib.load(f)        
                pyproject_version = data.get("project", {}).get("requires-python", None)
            if pyproject_version:
                version = pyproject_version.rstrip()
            else:
                version = None
        if version:
            #TODO sanity check on version
            return version
        # TODO: log using default version
        return self.default_python_version

    def detect(self):
        """Check if current repo contains a Python project."""
        requirements_txt = self.binder_path("requirements.txt")
        pipfile = self.binder_path("Pipfile")
        pipfile_lock = self.binder_path("Pipfile.lock")

        project_config_files = ["setup.py", "pyproject.toml"]
        for f in project_config_files:
            if (dep_file := self.binder_path(f)).exists():
                self.dependency_file = dep_file
                return True

        has_pip_or_req_file = False
        for f in [requirements_txt, pipfile_lock, pipfile]:
            if f.exists():
                self.dependency_file = f
                has_pip_or_req_file = True
        if has_pip_or_req_file:
            return True

        name = self.runtime[0]
        if name == "python":
            return True

        if super().python_version:
            return True

    def interpreter_version(self):
        return self.python_version
