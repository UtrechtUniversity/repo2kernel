from .base import Project
import tomllib

class PythonProject(Project):

    name = "Python"
    dependencies = ['uv']
    kernel_base_display_name = "Python Kernel"
    default_python_version="3"
    kernel_package_py = "ipykernel"

    def __init__(self, path, log, **kwargs):
        self.use_requirements_txt = False
        self.use_pipfile = False
        self.use_pipfile_lock = False
        super().__init__(path, log, **kwargs)

    def create_environment(self, env_create_path, interpreter_base_dir="", dry_run=False):
        Project.create_environment(self, env_create_path) # sanity checks
        env = {
            "VIRTUAL_ENV": env_create_path,
        }

        if interpreter_base_dir:
            env["UV_PYTHON_INSTALL_DIR"] = interpreter_base_dir

        cmds = [
            ["uv", "python", "install", self.interpreter_version],
            ["uv", "venv", env_create_path, "--python", self.interpreter_version]
        ]

        if self.use_requirements_txt:
            cmds.append(["uv", "pip", "install", "-r", str(self.binder_path('requirements.txt').resolve())])
        elif self.use_pipfile_lock:
            cmds.append(["uvx", "pipenv", "install", "--ignore-pipfile --dev"])
        elif self.use_pipfile:
            cmds.append(["uvx", "pipenv", "install", "--skip-lock", "--dev"])
        else:
            cmds.append(["uv", "pip", "install", str(self.binder_dir)])

        cmds.append(["uv", "pip", "install", self.kernel_package_py])

        self.run(cmds, env, dry_run=dry_run)
        return True

    def create_kernel(self,  env_path, user=False, name="", display_name="", prefix="", base_cmd=["uv", "run", "--active"], dry_run=False):
        Project.create_kernel(self, env_path) # sanity checks

        options = {
            'name': name or self.env_name,
            'display_name': display_name or self.kernel_display_name(),
            'user': user,
            'prefix': prefix
        }

        cmds = [
            [*base_cmd, "python", "-m", self.kernel_package_py, "install", *self.__class__.dict2cli(options)]
        ]

        self.run(cmds, { "VIRTUAL_ENV": env_path }, dry_run)
        return True

    @property
    def interpreter_version(self):
        runtime_version = self.runtime[1]
        if runtime_version:
            return runtime_version

        python_version = self.path / ".python-version"
        if python_version.exists():
            return python_version.read_text()

        pyproject = self.path / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject.resolve(), "rb") as f:
                data = tomllib.load(f)        
                pyproject_version = data.get("project", {}).get("requires-python", None)
            if pyproject_version:
                return pyproject_version

        # TODO: log using default version
        return self.default_python_version

    def detect(self):
        """Check if current repo contains a Python project."""
        requirements_txt = self.binder_path("requirements.txt")
        pipfile = self.binder_path("Pipfile")
        pipfile_lock = self.binder_path("Pipfile.lock")
        project_config_files = ["setup.py", "pyproject.toml"]

        for f in project_config_files:
            if self.binder_path(f).exists():
                return True

        self.use_requirements_txt = requirements_txt.exists()
        self.use_pipfile_lock = pipfile_lock.exists()
        self.use_pipfile = pipfile.exists()

        name = self.runtime[0]
        if name:
            return name == "python"
        return self.use_requirements_txt or self.use_pipfile_lock or self.use_pipfile
