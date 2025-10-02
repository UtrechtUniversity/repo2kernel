from .conda import CondaProject
from .base import Project
from repo2docker.buildpacks import JuliaProjectTomlBuildPack

import platform
import os
from pathlib import Path

class JuliaProject(CondaProject, JuliaProjectTomlBuildPack):

    project_type = "julia"
    kernel_base_display_name = "Julia Kernel"
    dependencies = ["juliaup"]
    kernel_package_julia = "IJulia"
    default_interpreter_base_dir = Path(os.environ.get("JULIAUP_DEPOT_PATH", "/usr/local/julia/"))
    default_kernel_location = (Path("%PROGRAMDATA/jupyter" if platform.system() == 'Windows' else "/usr/local/share/jupyter")).resolve()

    def __init__(self, project_path, env_base_path, log, **kwargs):
        kwargs["env_type"] = kwargs.get("env_type", "julia")
        CondaProject.__init__(self, project_path, env_base_path, log, **kwargs)
        self.detected = JuliaProjectTomlBuildPack.detect(self)
        self.interpreter_base_dir = self.default_interpreter_base_dir
        if self.conda_env_initialized:
            self.julia_depot_path = str(self.env_path / "lib/julia")
        else:
            self.julia_depot_path = str(self.env_path)

    def julia_env(self):
        return {
            'JULIAUP_DEPOT_PATH': str(self.interpreter_base_dir),
            'JULIA_DEPOT_PATH': self.julia_depot_path,
            'JULIA_PROJECT': ''
        }

    @Project.check_detected
    @Project.check_dependencies
    def create_environment(self, interpreter_base_dir="", **kwargs):
        if interpreter_base_dir:
            self.interpreter_base_dir = Path(interpreter_base_dir)

        v = self.interpreter_version
        cmds = [
            ["juliaup", "add", v],
            #["julia", f"+{v}", f"--project={self.project_path}", "-e", "using Pkg; Pkg.instantiate(); Pkg.resolve(); Pkg.instantiate();"]
        ]

        self.run(cmds, self.julia_env())

        return True

    @Project.check_detected
    def create_kernel(self, name="", display_name = "", user=False, prefix="", **kwargs):
        _name = name or self.env_name
        _display_name = display_name or self.kernel_display_name()

        env = self.julia_env()
        if not user:
            env['JUPYTER_DATA_DIR'] = str(prefix or self.default_kernel_location)
        else:
            pass # use the JUPYTER_DATA_DIR from, or the default user location for IJulia

        cmds = [
            ["julia", f"+{self.interpreter_version}", "-e", f"using Pkg; Pkg.add(\"IJulia\"); using IJulia; installkernel(\"{_name}\", \"--project={self.project_path}\", displayname=\"{_display_name}\", env=Dict(\"JULIA_DEPOT_PATH\"=>\"{self.julia_depot_path}\"));"],
        ]
        self.run(cmds, env)
        return True

    @property
    def interpreter_version(self):
        return super().julia_version
