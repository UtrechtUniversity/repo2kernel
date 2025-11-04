from .conda import CondaProject
from .base import Project
from repo2docker.buildpacks import JuliaProjectTomlBuildPack

import platform
import os
from pathlib import Path
import shutil
from packaging.version import Version, InvalidVersion

class JuliaProject(CondaProject, Project, JuliaProjectTomlBuildPack):

    JULIA_SUPPORTS_NAMED_ENV = "1.7.0"
    default_version = "1.12"
    project_type = "julia"
    kernel_base_display_name = "Julia Kernel"
    dependencies = ["juliaup"]
    kernel_package_julia = "IJulia"
    default_kernel_location = (Path("%PROGRAMDATA/jupyter" if platform.system() == 'Windows' else "/usr/local/share/jupyter")).resolve()

    def __init__(self, project_path, env_base_path, log, dry_run=False, force_init=False, **kwargs):
        CondaProject.__init__(self, project_path, env_base_path, log, dry_run=dry_run, force_init=force_init, **kwargs)
        self.detected = JuliaProjectTomlBuildPack.detect(self)

        # Since Julia stores all dependencies (including different version of the same package) in a single depot, set the env_path to the generic "julia" dir under the requested env_base_path, instead of env_base_path / julia / project_name
        self.env_path = self.env_base_path / "julia"

        if self.detected or force_init:
            try:
                parsed_version = Version(self.interpreter_version)
                if parsed_version < Version(self.JULIA_SUPPORTS_NAMED_ENV):
                    raise RuntimeError(f"Julia < {self.JULIA_SUPPORTS_NAMED_ENV} is not supported")

            named_env = self.env_path / "environments" / self.env_name / "Project.toml"
            if not dry_run:
                os.makedirs(named_env.parent, exist_ok=True)
                if (p := self.project_path / "Project.toml") and p.exists():
                    shutil.copy(p, named_env)
            self.julia_project_dir = f"@{self.env_name or '.'}"

    def julia_env(self):
        return {
            'JULIA_DEPOT_PATH': str(self.env_path),
            'JULIAUP_DEPOT_PATH': str(self.env_path),
            'JULIA_PROJECT': '',
        }

    @Project.check_detected
    @CondaProject.conda_install_dependencies # decide if we want this for Julia projects -- it installs juliaup in an otherwise unrelated conda environment (if it exists)
    @Project.check_dependencies
    def create_environment(self, **kwargs):
        v = self.interpreter_version
        cmds = [
            [*self.base_cmd, "juliaup", "add", v],
            [*self.base_cmd, "julia", f"+{v}", f"--project={self.julia_project_dir}", "-e", "using Pkg; Pkg.add(\"IJulia\"); Pkg.resolve(); Pkg.instantiate();"]
        ]

        self.run(cmds, self.julia_env())
        return True

    @Project.check_detected
    def create_kernel(self, name="", display_name = "", user=False, prefix="", **kwargs):
        env = self.julia_env()

        _name = f"julia-{name or self.env_name}"
        _display_name = self.kernel_display_name(display_name)

        if not user:
            env['JUPYTER_DATA_DIR'] = str(prefix or self.default_kernel_location)
        # IJulia installs kernels in userspace by default, so no need to do anyting if user is False

        cmds = [
            [*self.base_cmd, "julia", f"+{self.interpreter_version}", f"--project={self.julia_project_dir}", "-e", f"using Pkg; using IJulia; installkernel(\"{_name}\", \"--project={self.julia_project_dir}\", displayname=\"{_display_name}\", env=Dict(\"JULIA_DEPOT_PATH\"=>\":{env.get('JULIA_DEPOT_PATH')}\"));"],
        ]
        # Todo: check if DEPOT_PATH should always be the same
        self.run(cmds, env)
        return True

    @property
    def interpreter_version(self):
        if not self._interpreter_version: # self._interpreter_version is set either by Package.init() (to default_version) or by this method
            if self.detected:                
                v = super().julia_version
                try:
                    parsed_version = Version(v)
                    # juliaup expects 1.12 instead of 1.12.0, but in case of a prerelease it does expect e.g. 1.12-rc1
                    # however, super().julia_version returns 1.12.0 instead of 1.12 (only for point releases)
                    # so only if we have a version of the form x.y.0, return x.y instead
                    if len(parsed_version.release) == 3 and parsed_version.release[-1] == 0 and not parsed_version.is_prerelease and not parsed_version.is_postrelease:
                        self._interpreter_version = f"{parsed_version.major}.{parsed_version.minor}"
                    else:
                        self._interpreter_version = v
                except InvalidVersion:
                    return None
            else:
                return None
        return self._interpreter_version
