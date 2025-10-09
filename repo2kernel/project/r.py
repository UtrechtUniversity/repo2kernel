from .conda import CondaProject
from .base import Project
from repo2docker.buildpacks.r import RBuildPack

import platform
import datetime

class RProject(CondaProject, RBuildPack):
    project_type = "R"
    kernel_base_display_name = "R Kernel"
    dependencies = ["conda", "jupyter"]
    r_base_pkg = "conda-forge::r-base"
    kernel_package_r = "conda-forge::r-irkernel"
    default_posit_cran = "https://packagemanager.posit.co/cran/"
    r_default_opts = ["R", "--no-site-file", "--no-save", "--no-restore", "--no-init-file", "--no-environ", "--quiet", "-e"]
    default_version = "4.4.2" # this mimicks the default r version in repo2docker (2025.8.0)

    def __init__(self, project_path, env_base_path, log, interpreter_version="", force_init=False, **kwargs):
        if not kwargs.get("env_type"):
            kwargs["env_type"] = "conda"
        super().__init__(project_path, env_base_path, log, force_init=True, interpreter_version=interpreter_version, **kwargs)
        self.detected = self.detect()
        if self.detected or force_init:
            CondaProject.create_environment(self)

    def get_rspm_snapshot_url(self, max_days_prior=7):
        ubuntu_url = RBuildPack.get_rspm_snapshot_url(self, self.checkpoint_date or self.default_checkpoint_date(), max_days_prior) # RBuildPack constructs a download URL for Ubuntu specifically
        upsi = ubuntu_url.split('/')[-1] # returns a snapshot ID of the form '2025-09-24+GZQrDcph'
        upsi_date = upsi[:10] # get only the date info

        if platform.system() == 'Linux' and  platform.freedesktop_os_release().get('NAME') == 'Ubuntu':
            return ubuntu_url
        else:
            return f"{self.default_posit_cran}{upsi_date}"

    def cmd_r_create_kernel(self, name="", display_name="", prefix="", user=False):
        args = []

        _display_name = self.kernel_display_name(display_name)
        _name = f"R-{name or self.env_name}"

        args.append(f"displayname='{_display_name}'")
        args.append(f"name='{_name}'")
    
        if prefix:
            args.append(f"prefix='{prefix}'")
        if user:
            args.append("user=TRUE")
        else:
            args.append("user=FALSE")
        print(args)

        return [f"IRkernel::installspec({','.join(args)})"]
        

    @Project.check_detected
    @CondaProject.conda_install_dependencies
    @Project.check_dependencies
    def create_environment(self,  **kwargs):
        install_pkgs = [self.kernel_package_r, "r-devtools"]
        if not super().uses_r or not super().r_version:
            # if no r version was explicitly defined in conda environment.yml, install the version we detect (or the default version)
           install_pkgs.insert(0, self.__class__.conda_version(self.r_base_pkg, self.interpreter_version))
        self.conda_install(*install_pkgs)

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
        # TODO: remove temp package directories

        return True

    @Project.check_detected
    @Project.check_dependencies
    def create_kernel(self, **kwargs):
        cmds = [
            [*self.base_cmd, *self.r_default_opts, *self.cmd_r_create_kernel(**kwargs)]
        ]
        self.run(cmds, {})
        return True

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

        if (self.project_path / "DESCRIPTION").exists() or super().uses_r:
            # no R snapshot date set through runtime.txt
            # Set it to two days ago from today
            self._checkpoint_date = self.default_checkpoint_date()
            return True

    def default_checkpoint_date(self):
        return datetime.date.today() - datetime.timedelta(days=2)

    @property
    def interpreter_version(self):
        return super().interpreter_version or super(CondaProject, self).r_version or super(RBuildPack, self).r_version
