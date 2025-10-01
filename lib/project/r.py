from .conda import CondaProject
from .base import Project

import datetime

class RCondaProject(CondaProject):
    project_type = "R"
    kernel_base_display_name = "R Kernel"
    dependencies = []
    r_base_pkg = "conda-forge::r-base"
    kernel_package_r = "conda-forge::r-irkernel"

    def __init__(self, project_path, env_base_path, log, **kwargs):
        env_prefix = kwargs.get("env_prefix", "conda")
        kwargs["env_prefix"] = env_prefix
        super().__init__(project_path, env_base_path, log, force_init=True, **kwargs)
        self.dependency_file = ""
        self.detected = self.detect()

    def cmd_r_create_kernel(self, name="", display_name="", prefix="", user=False):
        args = []

        _display_name = display_name or self.kernel_display_name()
        args.append(f"displayname='{_display_name}'")

        if name:
            args.append(f"name='{name}'")
        if prefix:
            args.append(f"prefix='{prefix}'")
        if user:
            args.append("user=TRUE")
        else:
            args.append("user=FALSE")
        return [f"IRkernel::installspec({','.join(args)})"]

    @Project.check_detected
    @CondaProject.conda_install_dependencies
    @Project.check_dependencies
    def create_environment(self,  **kwargs):
        if not super().r_version:
            v = self.r_version
            if self.r_version or not super().uses_r:
                self.conda_install(self.__class__.conda_version(self.r_base_pkg, v))
        self.conda_install(self.kernel_package_r)

        # TODO: install additional dependencies from DESCRIPTION file if needed
        return True

    @Project.check_detected
    def create_kernel(self, **kwargs):
        cmds = [
            [*self.base_cmd, "R", "--quiet", "-e", *self.cmd_r_create_kernel(**kwargs)]
        ]
        self.run(cmds, {})
        return True

    # This method was copied from https://github.com/jupyterhub/repo2docker
    # Repo2docker is licensed under the BSD-3 license:
    # https://github.com/jupyterhub/repo2docker/blob/main/LICENSE
    # Copyright (c) 2017, Project Jupyter Contributors
    # All rights reserved.
    @property
    def checkpoint_date(self):
        """
        Return the date of CRAN checkpoint to use for this repo

        Returns '' if no date is specified
        """
        if not hasattr(self, "_checkpoint_date"):
            name, version, date = self.runtime
            if name == "r" and date:
                self._checkpoint_date = date
            else:
                self._checkpoint_date = False
        return self._checkpoint_date

    # This method was modified from https://github.com/jupyterhub/repo2docker
    # Repo2docker is licensed under the BSD-3 license:
    # https://github.com/jupyterhub/repo2docker/blob/main/LICENSE
    # Copyright (c) 2017, Project Jupyter Contributors
    # All rights reserved.
    def detect(self):
        """
        Check if current repo contains an R Project.

        Returns True if R was specified in runtime.txt, or
        a "DESCRIPTION" file is found in the repo root.
        """
        # If no date is found, then self.checkpoint_date will be False
        # Otherwise, it'll be a date object, which will evaluate to True
        if self.checkpoint_date:
            return True

        if (f := (self.project_path / "DESCRIPTION")).exists():
            self.dependency_file =f 
            # no R snapshot date set through runtime.txt
            # Set it to two days ago from today
            self._checkpoint_date = datetime.date.today() - datetime.timedelta(days=2)
            return True
        
        if super().uses_r:
            return True

    @property
    def r_version(self):
        # TODO: get version from DESCRIPTION
        return ""

    def interpreter_version(self):
        return super().r_version or self.r_version or ""
