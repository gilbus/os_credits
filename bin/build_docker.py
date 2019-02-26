#!/usr/bin/env python3
"""
Small helper script to supply the correct arguments to the docker build command.
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from getpass import getuser
from pathlib import Path
from subprocess import run
from sys import path

path.insert(0, str(Path(__file__).parent.parent.absolute()))


def main() -> int:
    from os_credits import __version__ as credits_version

    parser = ArgumentParser(
        description=__doc__, formatter_class=ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-u", "--username", help="Docker username", default=getuser())
    parser.add_argument(
        "-i", "--imagename", help="Docker imagename", default="os_credits"
    )

    args = parser.parse_args()

    run(
        [
            "docker",
            "build",
            "-t",
            "{}/{}:{}".format(args.username, args.imagename, credits_version),
            "--build-arg",
            "OS_CREDITS_VERSION={}".format(credits_version),
            ".",
        ]
    )
    return 0


if __name__ == "__main__":
    exit(main())
