from .base import Project

class RProject(Project):
    name = "R"
    kernel_base_display_name = "R Kernel"

    def __init__(self, project_path, env_path, log, **kwargs):
        Project.__init__(self, project_path, env_path, log, **kwargs)
        RProject.detect(self)

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

    def create_kernel(self, env_path, base_cmd=[], dry_run=False, **kwargs):
        Project.create_kernel(self, env_path) # sanity checks
        print(kwargs)
        cmds = [
            [*base_cmd, "R", "--quiet", "-e", *self.cmd_r_create_kernel(**kwargs)]
        ]
        self.run(cmds, {}, dry_run=dry_run)
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
    @Project.wrap_detect
    def detect(self):
        """
        Check if current repo contains an R Project.

        Returns True if R was specified in runtime.txt, or
        a "DESCRIPTION" file is found in the repo root.
        """
        # If no date is found, then self.checkpoint_date will be False
        # Otherwise, it'll be a date object, which will evaluate to True
        if self.checkpoint_date:
            return RProject

        if (f := (self.project_path / "DESCRIPTION")).exists():
            self.dependency_files["DESCRIPTION"] = str(f.resolve())
            # no R snapshot date set through runtime.txt
            # Set it to two days ago from today
            self._checkpoint_date = datetime.date.today() - datetime.timedelta(days=2)
            return RProject
