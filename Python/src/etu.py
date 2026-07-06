import sys


# =============
# Main
# =============


if len(sys.argv) < 2:
    print("Usage: etu <function_name> [args...]")
    sys.exit(1)

func_name = sys.argv[1]
func = globals().get(func_name)

if func is None:
    print(f"Unknown function: {func_name}")
    sys.exit(1)

func(*sys.argv[2:])


# =============
# Functions
# =============

