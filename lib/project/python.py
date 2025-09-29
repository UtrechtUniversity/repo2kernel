from .base import Project
import tomllib

class PythonProject(Project):

    name = "Python"
    dependencies = ['uv']
    kernel_base_display_name = "Python Kernel"
    default_python_version="3"
    kernel_package_py = "ipykernel"

    def __init__(self, project_path, env_path, log, **kwargs):
        Project.__init__(self, project_path, env_path, log, **kwargs)
        self.detected = self.detect()

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

    def create_environment(self, interpreter_base_dir="", install_python=True, dry_run=False):
        Project.create_environment(self, self.env_path) # sanity check

        if install_python:
            self.run(*self.cmd_install_python(interpreter_base_dir), dry_run=dry_run)
        if not self.env_path.exists():
            self.run(*self.cmd_init_environment(), dry_run=dry_run)

        cmds = []
        if f := self.dependency_files.get("requirements.txt"):
            cmds.append(["uv", "pip", "install", "-r", f])
        elif self.dependency_files.get("Pipfile.lock"):
            cmds.append(["uvx", "pipenv", "install", "--ignore-pipfile --dev"])
        elif self.dependency_files.get("Pipfile"):
            cmds.append(["uvx", "pipenv", "install", "--skip-lock", "--dev"])
        else:
            cmds.append(["uv", "pip", "install", str(self.binder_dir)])

        cmds.append(["uv", "pip", "install", self.kernel_package_py])

        self.run(cmds, {"VIRTUAL_ENV": str(self.env_path) }, dry_run=dry_run)
        return True

    def create_kernel(self, user=False, name="", display_name="", prefix="", base_cmd=["uv", "run", "--active"], dry_run=False):
        Project.create_kernel(self, self.env_path) # sanity checks

        options = {
            'name': name or self.env_name,
            'display_name': display_name or self.kernel_display_name(),
            'user': user,
            'prefix': prefix
        }

        cmds = [
            [*base_cmd, "python", "-m", self.kernel_package_py, "install", *self.__class__.dict2cli(options)]
        ]

        self.run(cmds, { "VIRTUAL_ENV": str(self.env_path) }, dry_run)
        return True

    @property
    def interpreter_version(self):
        runtime_version = self.runtime[1]
        if runtime_version:
            return runtime_version

        python_version = self.project_path / ".python-version"
        if python_version.exists():
            return python_version.read_text()

        pyproject = self.project_path / "pyproject.toml"
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
            if (dep_file := self.binder_path(f)).exists():
                self.dependency_files[dep_file] = str(dep_file)
                return True

        has_pip_or_req_file = False
        for f in [requirements_txt, pipfile_lock, pipfile]:
            if f.exists():
                self.dependency_files[f.name] = str(f)
                has_pip_or_req_file = True
        if has_pip_or_req_file:
            return True

        name = self.runtime[0]
        if name:
            return name == "python"
