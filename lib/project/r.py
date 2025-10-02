from .conda import CondaProject
from .base import Project
from repo2docker.buildpacks.r import RBuildPack

import platform
import datetime

class RCondaProject(CondaProject, RBuildPack):
    project_type = "R"
    kernel_base_display_name = "R Kernel"
    dependencies = ["conda"]
    r_base_pkg = "conda-forge::r-base"
    kernel_package_r = "conda-forge::r-irkernel"
    default_posit_cran = "https://packagemanager.posit.co/cran/"
    r_default_opts = ["R", "--no-site-file", "--no-save", "--no-restore", "--no-init-file", "--no-environ", "--quiet", "-e"]

    def __init__(self, project_path, env_base_path, log, **kwargs):
        env_type = kwargs.get("env_type", "conda")
        kwargs["env_type"] = env_type
        super().__init__(project_path, env_base_path, log, force_init=True, **kwargs)
        self.detected = self.detect()
        print(self.get_rspm_snapshot_url())

    def get_rspm_snapshot_url(self, max_days_prior=7):
        ubuntu_url = RBuildPack.get_rspm_snapshot_url(self, self.checkpoint_date, max_days_prior) # RBuildPack constructs a download URL for Ubuntu specifically
        upsi = ubuntu_url.split('/')[-1] # returns a snapshot ID of the form '2025-09-24+GZQrDcph'
        upsi_date = upsi[:10] # get only the date info

        if platform.system() == 'Linux' and  platform.freedesktop_os_release().get('NAME') == 'Ubuntu':
            return ubuntu_url
        else:
            return f"{self.default_posit_cran}{upsi_date}"

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
    def create_environment(self,  **kwargs):
        if not super().r_version:
            v = self.r_version
            if self.r_version or not super().uses_r:
                self.conda_install(self.__class__.conda_version(self.r_base_pkg, v))
        self.conda_install(self.kernel_package_r)
        self.conda_install("r-devtools")

        cmds = []
        repo = self.get_rspm_snapshot_url()

        if (f := self.binder_path("install.R")) and f.exists():
            cmds.append(
                [*self.base_cmd, *self.r_default_opts, f'options(repos=c(CRAN="{repo}"))', "-e", f"source('{f}')"]
            )

        if (f := self.project_path / "DESCRIPTION") and f.exists():
            cmds.append(
                [*self.base_cmd, *self.r_default_opts, f"devtools::install_local('{f.parent}', repos='{repo}')"]
            )

        self.run(cmds, {})

        return True

    @Project.check_detected
    def create_kernel(self, **kwargs):
        cmds = [
            [*self.base_cmd, *self.r_default_opts, *self.cmd_r_create_kernel(**kwargs)]
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

        if (self.project_path / "DESCRIPTION").exists():
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
