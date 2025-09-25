from .base import Project
import tomllib

class PythonProject(Project):

    name = "Python"
    dependencies = ['uv']
    kernel_base_display_name = "Python Kernel"
    default_python_version="3.13"

    def __init__(self, path, log, **kwargs):
        self.default_python_version = self.default_python_version
        self.use_requirements_txt = False
        super().__init__(path, log, **kwargs)

    def install_commands(self, env_create_path, **kwargs):
        super().install_commands(env_create_path, **kwargs)
        env = {
            "VIRTUAL_ENV": env_create_path,
        }

        if interpreter_base_dir := kwargs.get('interpreter_base_dir', False):
            env["UV_PYTHON_INSTALL_DIR"] = interpreter_base_dir
        dry_run = kwargs.get('dry_run', False)

        cmds =  [
                ["uv", "python", "install", self.interpreter_version],
                ["uv", "venv", env_create_path],
        ]

        if self.use_requirements_txt:
            cmds.append(f"uv pip install -r {self.binder_path('requirements.txt').resolve()}")
        elif self.use_pipfile_lock:
            cmds.append(f"uvx pipenv install --ignore-pipfile --dev")
        elif self.use_pipfile:
            cmds.append(f"uvx pipenv install --skip-lock --dev")
        else:
            cmds.append(["uv", "pip", "install", str(self.binder_dir)])

        cmds.append(["uv", "pip", "install", self.jupyter_kernel()])

        self.run(cmds, env, dry_run)
        return True # if no exception were thrown by run


    def install_kernel_commands(self, env_path, **kwargs):
        super().install_kernel_commands(env_path, **kwargs)

        dry_run = kwargs.get('dry_run', False)

        extra_kernel_opts = kwargs.get('extra_kernel_opts', {})
        options = {
            'name': kwargs.get('name') or self.env_name,
            'display_name': kwargs.get('display_name') or self.kernel_display_name(),
            **extra_kernel_opts
        }

        if user := kwargs.get('user', False):
            options['user'] = Trues
        if prefix := kwargs.get('prefix', False):
            options['prefix'] = prefix
    
        cmds, env = (
            [
                ["uv", "run", "--active", "python", "-m", self.jupyter_kernel(), "install", *self.__class__.dict2cli(options)]
            ],
            {
                "VIRTUAL_ENV": env_path,
            }
        )

        self.run(cmds, env, dry_run)
        return True # if no exception were thrown by run

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

    def jupyter_kernel(self):
        return "ipykernel"

    def detect(self):
        """Check if current repo should be built with the Python buildpack."""
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

