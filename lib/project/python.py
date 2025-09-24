from .base import Project
import tomllib

class PythonProject(Project):

    name = "Python"
    dependencies = ['uv']
    kernel_base_display_name = "Python Kernel"
    default_python_version="3.13"

    def __init__(self, path):
        self.default_python_version = self.default_python_version
        self.use_requirements_txt = False
        super().__init__(path)

    def install_commands(self, env_create_path, interpreter_base_dir=""):
        super()
        env = {
            "VIRTUAL_ENV": env_create_path,
        }
        print(self.use_requirements_txt)
        if interpreter_base_dir:
            env["UV_PYTHON_INSTALL_DIR"] = interpreter_base_dir

        cmds =  [
                ["uv", "python", "install", self.interpreter_version()],
                ["uv", "venv", env_create_path],
        ]

        if self.use_requirements_txt:
            cmds.append(f"uv pip compile {self.binder_path("requirements.txt")} | uv pip install -r -")
        else:
            cmds.append(["uv", "pip", "install", str(self.binder_dir)])
        
        cmds.append(["uv", "pip", "install", self.jupyter_kernel()])

        return (cmds, env)

    def install_kernel_commands(self, env_path, user=False, name="", display_name="", prefix="", **kwargs):
        super()
        options = {
            'name': name or self.env_name,
            'display_name': display_name or self.kernel_display_name(),
            **kwargs
        }
        if user:
            options['user'] = ''
        if prefix:
            options['prefix'] = prefix

        return (
            [
                ["uv", "run", "--active", "python", "-m", self.jupyter_kernel(), "install", *self.__class__.dict2cli(options)]
            ],
            {
                "VIRTUAL_ENV": env_path,
            }
        )

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
        project_config_files = ["setup.py", "pyproject.toml"]

        for f in project_config_files:
            if self.binder_path(f).exists():
                return True

        self.use_requirements_txt = requirements_txt.exists()

        name = self.runtime[0]
        if name:
            return name == "python"
        
        return self.use_requirements_txt
