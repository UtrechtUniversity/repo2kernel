from .conda import CondaProject

class RCondaProject(CondaProject):
    name = "R"
    kernel_base_display_name = "R Kernel"
    dependencies = []
    r_base_pkg = "conda-forge::r-base"
    kernel_package_r = "conda-forge::r-irkernel"
    cran_mirror = "http://cran.us.r-project.org"

    def __init__(self, project_path, env_path, log, lib_path="", **kwargs):
        super().__init__(project_path, env_path, log, force_init=True, **kwargs)
        self.dependency_file = ""
        self.detected = self.detect()

    def pkg_args(self):
        args = {
            'repos': self.cran_mirror
        }
        if (env_lib_path := self.env_path / "lib/R/library") and env_lib_path.exists():
            args['lib'] = str(env_lib_path)
        # TODO: set global lib path
        return ", ".join([f"{k}='{v}'" for k,v in args.items() if v is not None])

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
        return [f"{self.kernel_package_r}::installspec({','.join(args)})"]

    @CondaProject.conda_install_dependencies
    @Project.sanity_check
    def create_environment(self, base_cmd=[]):
        if not super().r_version: # r not declared in environment.yml, conda install it
            self.conda_install(f"{r_base_pkg}=={self.r_version}")
        self.conda_install(kernel_package_r)

        # TODO: install dependencies from DESCRIPTION file if needed
        return True

    @Project.sanity_check
    def create_kernel(self, base_cmd=[], **kwargs):
        cmds = [
            [*base_cmd, "R", "--quiet", "-e", *self.cmd_r_create_kernel(**kwargs)]
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

    @property
    def r_version(self):
        return "4.5.1"
