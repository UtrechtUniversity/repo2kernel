from pathlib import Path
from shutil import which
import uuid

class Project:

    name = "project"
    dependencies = []
    kernel_base_display_name = "Kernel"

    @classmethod
    def dict2cli(self, opts):
        return [f"--{k.replace('_', '-')}{f'={v}' if v else ''}" for k,v in opts.items()]

    def __init__(self, path, **kwargs):
        self.path = Path(path)
        self.env_name = f"{self.path.name}-{uuid.uuid4().hex}"
        self.detected = self.detect()
        self.version = self.interpreter_version()

    def kernel_display_name(self):
        return f"{self.kernel_base_display_name} {self.path.name}"

    def check_dependencies(self):
        for d in self.dependencies:
            if not which(d):
                raise RuntimeError(f"Dependency {d} for {self.__class__.__name__} not found.")
        return True

    def interpreter_version(self):
        return ""

    def jupyter_kernel(self):
        return ""

    def install_commands(self, env_create_path, interpreter_base_dir=""):
        if not self.detected:
            raise RuntimeError(f"Cannot install dependencies, no {self.name} environment detected in {str(self.path.resolve())}")
        if not env_create_path:
            raise RuntimeError("Missing required argument: env_create_path")
        self.check_dependencies()
        return ([], {})

    def install_kernel_commands(self, env_path, user=False, name="", display_name="", prefix="", **kwargs):
        if not self.detected:
            raise RuntimeError(f"Cannot install dependencies, no {self.name} environment detected in {str(self.path.resolve())}")
        self.check_dependencies()
        return ([], {})

    def detect(self):
        return True

    @property
    def runtime(self):
        """
        Return parsed contents of runtime.txt

        Returns (runtime, version, date), tuple components may be None.
        Returns (None, None, None) if runtime.txt not found.

        Supported formats:
          name-version
          name-version-yyyy-mm-dd
          name-yyyy-mm-dd
        """
        if hasattr(self, "_runtime"):
            return self._runtime

        self._runtime = (None, None, None)

        runtime_path = self.binder_path("runtime.txt")
        try:
            with open(runtime_path) as f:
                runtime_txt = f.read().strip()
        except FileNotFoundError:
            return self._runtime

        name = None
        version = None
        date = None

        parts = runtime_txt.split("-")
        if len(parts) not in (2, 4, 5) or any(not (p) for p in parts):
            raise ValueError(f"Invalid runtime.txt: {runtime_txt}")

        name = parts[0]

        if len(parts) in (2, 5):
            version = parts[1]

        if len(parts) in (4, 5):
            date = "-".join(parts[-3:])
            if not re.match(r"\d\d\d\d-\d\d-\d\d", date):
                raise ValueError(f"Invalid runtime.txt date: {date}")
            date = datetime.datetime.fromisoformat(date).date()

        self._runtime = (name, version, date)
        return self._runtime

    @property
    def binder_dir(self):
        binder_path = self.path / "binder"
        dotbinder_path = self.path / ".binder"

        has_binder = binder_path.is_dir()
        has_dotbinder = dotbinder_path.is_dir()

        if has_binder and has_dotbinder:
            raise RuntimeError(
                "The repository contains both a 'binder' and a '.binder' "
                "directory. However they are exclusive."
            )

        if has_dotbinder:
            return dotbinder_path
        elif has_binder:
            return binder_path
        else:
            return self.path

    def binder_path(self, path):
        """Locate a file"""
        return self.binder_dir / path

    def detect(self):
        """Check if project contains the kind of environment we're looking for."""
        return False

