from repo2docker.contentproviders import Dataverse as BaseDataverse
import os

class Dataverse(BaseDataverse):
    """
    Provide contents of a Dataverse dataset.

    This class extends the default Dataverse class from repo2docker to allow adding
    arbitrary dataverse hosts using a custom json file.
    """

    settings_files = set()

    def __init__(self):
        super().__init__()
        for settings_file in self.settings_files:
            # TODO: error handling
            with open(settings_file) as fp:
                self.hosts.extend(json.load(fp)["installations"])

    @classmethod
    def add_settings_file(cls, file):
        return setattr(cls, "settings_file", cls.settings_files.add(file))
