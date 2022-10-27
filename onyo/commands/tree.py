import logging
import os
import sys

from onyo.utils import (
    run_cmd
)
from onyo.lib import Repo, OnyoInvalidRepoError

logging.basicConfig()
log = logging.getLogger('onyo')


def build_tree_cmd(directory):
    if not os.path.isdir(directory):
        log.error(directory + " does not exist.")
        sys.exit(1)
    return "tree \"" + directory + "\""


def prepare_arguments(sources, opdir):
    problem_str = ""
    list_of_sources = []
    # just a single path?
    single_source = "".join(sources)
    if os.path.isdir(single_source):
        return [single_source]
    elif os.path.isdir(os.path.join(opdir, single_source)):
        return [os.path.join(opdir, single_source)]
    # build paths
    for source in sources:
        current_source = source
        if not os.path.exists(current_source):
            current_source = os.path.join(opdir, source)
        # check if path exists
        if not os.path.exists(current_source):
            problem_str = problem_str + "\n" + source + " does not exist."
        elif not os.path.isdir(current_source):
            problem_str = problem_str + "\n" + source + " is not a directory."
        else:
            list_of_sources.append(current_source)
    if problem_str != "":
        log.error(problem_str)
        sys.exit(1)
    return list_of_sources


def tree(args, opdir):
    """
    List the assets and directories in ``directory`` using the ``tree``
    program.
    """
    try:
        repo = Repo(opdir)
        repo.fsck(['asset-yaml'])
    except OnyoInvalidRepoError:
        sys.exit(1)

    # check sources
    list_of_sources = prepare_arguments(args.directory, opdir)
    # build and run commands
    for source in list_of_sources:
        tree_command = build_tree_cmd(source)
        output = run_cmd(tree_command)
        print(output)
