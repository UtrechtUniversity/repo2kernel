from .conda import CondaProject
from .base import Project
from repo2docker.buildpacks import JuliaProjectTomlBuildPack

import platform
import os
from pathlib import Path
import shutil
from packaging.version import Version

class JuliaProject(CondaProject, JuliaProjectTomlBuildPack):

    JULIA_SUPPORTS_NAMED_ENV = "1.7.0"
    project_type = "julia"
    kernel_base_display_name = "Julia Kernel"
    dependencies = ["juliaup"]
    kernel_package_julia = "IJulia"
    default_kernel_location = (Path("%PROGRAMDATA/jupyter" if platform.system() == 'Windows' else "/usr/local/share/jupyter")).resolve()

    def __init__(self, project_path, env_base_path, log, **kwargs):
        kwargs["env_type"] = kwargs.get("env_type", "julia")
        CondaProject.__init__(self, project_path, env_base_path, log, **kwargs)
        self.detected = JuliaProjectTomlBuildPack.detect(self)
        self.julia_project_dir = self.project_path
        # Since Julia stores all dependencies (including different version of the same package) in a single depot, set the env_path to the generic "julia" dir under the requested env_base_path, instead of env_base_path / julia / project_name
        self.env_path = self.env_base_path / "julia"

    def julia_env(self):
        return {
            'JULIA_DEPOT_PATH': str(self.env_path),
            'JULIAUP_DEPOT_PATH':  str(self.env_path),
            'JULIA_PROJECT': ''
        }

    @Project.check_detected
    @Project.check_dependencies
    def create_environment(self, **kwargs):
        v = self.interpreter_version

        if Version(v) >= Version(self.JULIA_SUPPORTS_NAMED_ENV):
            named_env = Path(env['JULIA_DEPOT_PATH']) / "environments" / self.env_name / "Project.toml"
            os.makedirs(named_env.parent, exist_ok=True)
            shutil.copy(self.project_path / "Project.toml", named_env)
            self.julia_project_dir = f"@{self.env_name}"

        cmds = [
            ["juliaup", "add", v],
            ["julia", f"+{v}", f"--project={self.julia_project_dir}", "-e", "using Pkg; Pkg.add(\"IJulia\"); Pkg.instantiate(); Pkg.resolve(); Pkg.instantiate();"]
        ]

        self.run(cmds, self.julia_env())
        return True

    @Project.check_detected
    def create_kernel(self, name="", display_name = "", user=False, prefix="", **kwargs):
        env = self.julia_env()

        _name = name or self.env_name
        _display_name = display_name or self.kernel_display_name()

        if not user:
            env['JUPYTER_DATA_DIR'] = str(prefix or self.default_kernel_location)
        # IJulia installs kernels in userspace by default, so no need to do anyting if user is False

        cmds = [
            ["julia", f"+{self.interpreter_version}", "--project=@temp", "-e", f"using Pkg; using IJulia; installkernel(\"{_name}\", \"--project={self.julia_project_dir}\", displayname=\"{_display_name}\", env=Dict(\"JULIA_DEPOT_PATH\"=>\"{env.get('JULIA_DEPOT_PATH')}\"));"],
        ]
        # Todo: check if DEPOT_PATH should always be the same
        self.run(cmds, env)
        return True

    @property
    def interpreter_version(self):
        return super().julia_version
