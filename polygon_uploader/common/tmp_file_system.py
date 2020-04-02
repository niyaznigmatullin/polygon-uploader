import tempfile
import shutil
import atexit


def create_temporary_directory(prefix):
    directory = tempfile.mkdtemp(prefix=prefix)

    def cleaner(dir_to_remove):
        def do_cleaner():
            shutil.rmtree(dir_to_remove)
        return do_cleaner

    atexit.register(cleaner(directory))
    return directory
