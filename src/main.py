"""

Author: DuBoLEE, MCHIGM

Last updated: 20260812

"""

# ========================================= 1. Engine setup =========================================


#############
# Imports
#############


# Library

# Debugging
import logging

# Essentials
import sys

import lib

#############
# Configuration
#############


VERSION = "0.1.0"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

log = logging.getLogger("etu")


# ========================================= 2. Command loop =========================================


def dispatch(io, command):
    """Run one command. Returns False when the engine should stop."""
    if command in ("exit", "quit"):
        io.exit()
        return False

    if command == "help":
        io.help()
    elif command == "files":
        io.files()
    elif command == "version":
        io.say(f"Project ETU {VERSION}")
    elif command:
        io.warn(f"unknown command: {command} (try 'help')")

    return True


def loop(io):
    """Read and run commands until the user stops or input ends."""
    while True:
        command = io.read()

        if command is None:
            io.exit()
            return

        if not dispatch(io, command):
            return


# ========================================= 3. Entry point =========================================


def main(argv=None):
    """Run one command from argv, or start the interactive loop."""
    argv = sys.argv[1:] if argv is None else argv
    io = lib.BASIC_IO()

    if argv:
        dispatch(io, " ".join(argv))
        return 0

    io.say(f"Project ETU {VERSION} - type 'help' for commands.")
    loop(io)
    return 0


if __name__ == "__main__":
    sys.exit(main())
