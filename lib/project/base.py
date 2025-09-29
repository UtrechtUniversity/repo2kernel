from pathlib import Path
from shutil import which
import uuid
import subprocess, os

class Project:

    name = "project"
    dependencies = []
    kernel_base_display_name = "Kernel"

    @classmethod
    def dict2cli(self, opts):
        return [f"--{k.replace('_', '-')}{f'={v}'}" for k,v in opts.items() if v]

    def __init__(self, project_path, env_path, log, **kwargs):
        self.project_path = Path(project_path)
        self.env_name = f"{self.project_path.name}-{uuid.uuid4().hex}"
        self.env_path = env_path
        self.detected = self.detect()
        self.log = log

    def kernel_display_name(self):
        return f"{self.kernel_base_display_name} {self.project_path.name}"

    def check_dependencies(self):
        for d in self.dependencies:
            if not which(d):
                raise RuntimeError(f"Dependency {d} for {self.__class__.__name__} not found.")
        return True

    @property
    def interpreter_version(self):
        return ""

    def create_environment(self, interpreter_base_dir="", dry_run=False):
        if not self.detected:
            raise RuntimeError(f"Cannot install dependencies, no {self.name} environment detected in {self.project_path.resolve()}")
        self.check_dependencies()
        self.log.info(f"CREATE {self.name} VENV: Attempting to install dependencies for {self.project_path.resolve()} into {self.env_path}.")

    def create_kernel(self, user=False, name="", display_name="", prefix="", dry_run=True, extra_kernel_opts={}):
        if not self.detected:
            raise RuntimeError(f"Cannot install dependencies, no {self.name} environment detected in {self.project_path.resolve()}")
        self.check_dependencies()
        self.log.info(f"CREATE KERNEL: Attempting to create kernel for {self.project_path.resolve()}.")

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
        binder_path = self.project_path / "binder"
        dotbinder_path = self.project_path / ".binder"

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
            return self.project_path

    def binder_path(self, path):
        """Locate a file"""
        return self.binder_dir / path

    def detect(self):
        """Check if project contains the kind of environment we're looking for."""
        return False

    def run(self, commands, env, dry_run=False):
        self.log.info("Will run the following commands:")
        for cmd in commands:
            self.log.info(cmd)
        if len(env.keys()) > 0:
            self.log.info("...with the following environment variables:")
            for k,v in env.items():
                self.log.info(f"{k}={v}")
        if not dry_run:
            for cmd in commands:
                p = subprocess.Popen(cmd, env=(os.environ.copy() | env), shell=isinstance(cmd, str))
                exit_code = p.wait()
                if exit_code > 0:
                    raise RuntimeError(f"Error! repo2kernel is aborting after the following command failed:\n{cmd}")
                else:
                    self.log.info("...success")
        return True
