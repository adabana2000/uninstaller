"""
Main entry point for the Windows Uninstaller application.
Can be run in CLI mode or GUI mode.
"""

import sys
import argparse
from cli.commands import cli as cli_main


def main():
    """
    Main entry point.

    Determines whether to run in CLI or GUI mode based on command-line arguments.
    If no arguments are provided, defaults to GUI mode.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Windows Uninstaller - Advanced application uninstaller",
        add_help=False
    )
    parser.add_argument("--gui", action="store_true", help="Launch GUI mode")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode")

    # Parse known args to avoid conflicts with Click
    args, remaining = parser.parse_known_args()

    # Determine mode
    if args.cli or (remaining and not args.gui):
        # CLI mode if explicitly requested or if there are CLI arguments
        # Pass remaining arguments to Click
        sys.argv = [sys.argv[0]] + remaining
        cli_main()
    else:
        # Default to GUI mode (when no arguments or --gui is specified)
        try:
            from gui.main_window import launch_gui
            launch_gui()
        except ImportError as e:
            print(f"Error: GUI dependencies not installed: {e}")
            print("Please install PyQt6: pip install PyQt6")
            sys.exit(1)


if __name__ == "__main__":
    main()
