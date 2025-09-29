from .base import Project
import tomllib

class PythonProject(Project):

    name = "Python"
    kernel_base_display_name = "Python Kernel"
    default_python_version="3"
    dependencies = ["uv"]
    kernel_package_py = "ipykernel"

    def __init__(self, project_path, env_path, log, **kwargs):
        Project.__init__(self, project_path, env_path, log, **kwargs)
        PythonProject.detect(self)


    @Project.sanity_check
    def create_environment(self, interpreter_base_dir="", base_cmd=[], dry_run=False):
        if not self.env_path.exists():
            if dry_run:
                self.log.info("Because we are in dry run mode, cannot ascertain if the enviroment directory was already created. Will proceed as if it was not.")
            env = {}
            if interpreter_base_dir:
                env["UV_PYTHON_INSTALL_DIR"] = interpreter_base_dir
            cmds = [
                ["uv", "python", "install", self.python_version],
                ["uv", "venv", str(self.env_path), "--python", self.python_version]
            ]
            self.run(cmds, env, dry_run=dry_run)

        cmds = []

        if f := self.dependency_files.get("requirements.txt"):
            cmds.append([*base_cmd, "uv", "pip", "install", "-r", f])
        elif self.dependency_files.get("Pipfile.lock"):
            cmds.append([*base_cmd, "uvx", "pipenv", "install", "--ignore-pipfile --dev"])
        elif self.dependency_files.get("Pipfile"):
            cmds.append([*base_cmd, "uvx", "pipenv", "install", "--skip-lock", "--dev"])
        elif self.dependency_files.get("setup.py") or self.dependency_files.get("pyproject.toml"):
            cmds.append([*base_cmd, "uv", "pip", "install", str(self.binder_dir)])
        cmds.append([*base_cmd, "uv", "pip", "install", self.kernel_package_py])

        self.run(cmds, {"VIRTUAL_ENV": str(self.env_path) }, dry_run=dry_run)

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
            [*base_cmd, "uv", "run", "--active", "python", "-m", self.kernel_package_py, "install", *self.__class__.dict2cli(options)]
        ]

        self.run(cmds, { "VIRTUAL_ENV": str(self.env_path) }, dry_run)
        return True

    @property
    def python_version(self):
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
