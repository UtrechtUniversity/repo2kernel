from .base import Project

class RProject(Project):
    name = "R"
    kernel_base_display_name = "R Kernel"

    def r_create_kernel_cmd(self, name="", display_name="", prefix="", user=False):
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
            [*base_cmd, "R", "--quiet", "-e", *self.r_create_kernel_cmd(**kwargs)]
        ]
        self.run(cmds, {}, dry_run=dry_run)
        return True
