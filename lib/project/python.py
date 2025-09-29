from .base import Project
import tomllib

class PythonProject(Project):

    name = "Python"
    kernel_base_display_name = "Python Kernel"
    default_python_version="3"
    kernel_package = "ipykernel"
    dependencies = ["uv"]

    def __init__(self, project_path, env_path, log, **kwargs):
        Project.__init__(self, project_path, env_path, log, **kwargs)
        PythonProject.detect(self)

    def cmd_install_python(self, interpreter_base_dir):
        env = {}
        if interpreter_base_dir:
            env["UV_PYTHON_INSTALL_DIR"] = interpreter_base_dir
        cmds = [
            ["uv", "python", "install", self.interpreter_version]
        ]
        return (cmds, env)

    def cmd_init_environment(self):
        cmds =  [
            ["uv", "venv", str(self.env_path), "--python", self.interpreter_version]
        ]
        return (cmds, {})

    @Project.sanity_check
    def install_env_dependencies(self, base_cmd=[], dry_run=False):
        cmds = []
        if f := self.dependency_files.get("requirements.txt"):
            cmds.append([*base_cmd, "uv", "pip", "install", "-r", f])
        elif self.dependency_files.get("Pipfile.lock"):
            cmds.append([*base_cmd, "uvx", "pipenv", "install", "--ignore-pipfile --dev"])
        elif self.dependency_files.get("Pipfile"):
            cmds.append([*base_cmd, "uvx", "pipenv", "install", "--skip-lock", "--dev"])
        else:
            cmds.append([*base_cmd, "uv", "pip", "install", str(self.binder_dir)])
        cmds.append([*base_cmd, "uv", "pip", "install", self.kernel_package])

        self.run(cmds, {"VIRTUAL_ENV": str(self.env_path) }, dry_run=dry_run)

    def create_environment(self, interpreter_base_dir="", dry_run=False):
        self.run(*self.cmd_install_python(interpreter_base_dir), dry_run=dry_run)
        if not self.env_path.exists():
            self.run(*self.cmd_init_environment(), dry_run=dry_run)

        self.install_env_dependencies(dry_run=dry_run)

        return True

    @Project.sanity_check
    def create_kernel(self, user=False, name="", display_name="", prefix="", base_cmd=[], dry_run=False):
        Project.create_kernel(self, self.env_path) # sanity checks

        options = {
            'name': name or self.env_name,
            'display_name': display_name or self.kernel_display_name(),
            'user': user,
            'prefix': prefix
        }

        cmds = [
            [*base_cmd, "uv", "run", "--active", "python", "-m", self.kernel_package, "install", *self.__class__.dict2cli(options)]
        ]

        self.run(cmds, { "VIRTUAL_ENV": str(self.env_path) }, dry_run)
        return True

    def get_interpreter_version(self):
        runtime_version = self.runtime[1]
        if runtime_version:
            return runtime_version.rstrip()

        python_version = self.project_path / ".python-version"
        if python_version.exists():
            return python_version.read_text().rstrip()

        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject.resolve(), "rb") as f:
                data = tomllib.load(f)        
                pyproject_version = data.get("project", {}).get("requires-python", None)
            if pyproject_version:
                return pyproject_version.rstrip()

        # TODO: log using default version
        return self.default_python_version

    @property
    def interpreter_version(self):
        return self.get_interpreter_version()
    
    @Project.wrap_detect
    def detect(self):
        """Check if current repo contains a Python project."""
        requirements_txt = self.binder_path("requirements.txt")
        pipfile = self.binder_path("Pipfile")
        pipfile_lock = self.binder_path("Pipfile.lock")

        project_config_files = ["setup.py", "pyproject.toml"]
        for f in project_config_files:
            if (dep_file := self.binder_path(f)).exists():
                self.dependency_files[dep_file] = str(dep_file)
                return PythonProject

        has_pip_or_req_file = False
        for f in [requirements_txt, pipfile_lock, pipfile]:
            if f.exists():
                self.dependency_files[f.name] = str(f)
                has_pip_or_req_file = True
        if has_pip_or_req_file:
            return PythonProject

        name = self.runtime[0]
        if name == "python":
            return PythonProject
