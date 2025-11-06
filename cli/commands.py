"""
Command-line interface for the uninstaller application.
Uses Click framework for command parsing and execution.
"""

import click
import sys
import winreg
from tabulate import tabulate

# Add parent directory to path for imports
sys.path.insert(0, "..")

from core.registry import RegistryReader, get_installed_programs
from core.uninstaller import Uninstaller
from core.scanner import LeftoverScanner
from core.cleaner import Cleaner
from utils.system_info import get_system_info, print_system_info
from utils.permissions import is_admin, ensure_admin, print_privilege_info
from utils.logger import get_logger
from utils.backup import BackupManager


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """
    Windows Uninstaller - Advanced application uninstaller with leftover cleanup.

    This tool helps you completely remove applications from Windows,
    including leftover files and registry entries.
    """
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj["logger"] = get_logger()


@cli.command()
@click.option("--include-updates", is_flag=True, help="Include Windows updates in the list")
@click.option("--format", type=click.Choice(["table", "json", "simple"]), default="table", help="Output format")
@click.option("--search", help="Search for programs by name")
def list(include_updates, format, search):
    """List all installed programs."""
    logger = get_logger()
    logger.info("Scanning for installed programs...")

    reader = RegistryReader()
    programs = reader.get_installed_programs(include_updates=include_updates)

    # Apply search filter if provided
    if search:
        programs = reader.search_programs(search)
        logger.info(f"Found {len(programs)} programs matching '{search}'")
    else:
        logger.info(f"Found {len(programs)} installed programs")

    if not programs:
        click.echo("No programs found.")
        return

    # Format output
    if format == "json":
        import json
        data = [p.to_dict() for p in programs]
        click.echo(json.dumps(data, indent=2))

    elif format == "simple":
        for prog in programs:
            click.echo(f"{prog.name} ({prog.version or 'Unknown version'})")

    else:  # table format
        headers = ["Name", "Version", "Publisher", "Architecture"]
        rows = [
            [
                prog.name[:50] + "..." if len(prog.name) > 50 else prog.name,
                prog.version or "Unknown",
                prog.publisher or "Unknown",
                prog.architecture
            ]
            for prog in programs
        ]
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@cli.command()
@click.argument("program_name")
def info(program_name):
    """Show detailed information about a program."""
    logger = get_logger()
    logger.info(f"Searching for program: {program_name}")

    reader = RegistryReader()
    programs = reader.get_installed_programs()
    program = reader.get_program_by_name(program_name)

    if not program:
        # Try partial match
        matches = reader.search_programs(program_name)
        if not matches:
            click.echo(f"Program not found: {program_name}", err=True)
            return
        elif len(matches) > 1:
            click.echo(f"Multiple programs found matching '{program_name}':")
            for p in matches:
                click.echo(f"  - {p.name}")
            click.echo("\nPlease specify the exact program name.")
            return
        else:
            program = matches[0]

    # Display program information
    click.echo("\n" + "=" * 70)
    click.echo(f"Program Information: {program.name}")
    click.echo("=" * 70)
    click.echo(f"Version:           {program.version or 'Unknown'}")
    click.echo(f"Publisher:         {program.publisher or 'Unknown'}")
    click.echo(f"Install Date:      {program.install_date or 'Unknown'}")
    click.echo(f"Install Location:  {program.install_location or 'Unknown'}")
    click.echo(f"Estimated Size:    {program.estimated_size or 0} KB")
    click.echo(f"Architecture:      {program.architecture}")
    click.echo(f"Registry Key:      {program.registry_key}")
    click.echo(f"Uninstall String:  {program.uninstall_string or 'Unknown'}")
    click.echo(f"System Component:  {program.is_system_component}")
    click.echo("=" * 70 + "\n")


@cli.command()
@click.argument("program_name")
@click.option("--no-backup", is_flag=True, help="Skip creating backups")
@click.option("--silent/--interactive", default=True, help="Silent or interactive mode")
@click.option("--no-scan", is_flag=True, help="Skip scanning for leftovers")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
def uninstall(program_name, no_backup, silent, no_scan, yes):
    """
    Uninstall a program.

    This command will:
    1. Find the specified program
    2. Create backups (if not disabled)
    3. Run the uninstaller
    4. Scan for leftover files and registry entries
    5. Optionally clean up leftovers
    """
    logger = get_logger()

    # Check for admin privileges
    if not is_admin():
        click.echo("⚠ Administrator privileges required for uninstallation.", err=True)
        try:
            ensure_admin()
        except PermissionError as e:
            click.echo(str(e), err=True)
            sys.exit(1)

    logger.info(f"Preparing to uninstall: {program_name}")

    # Find the program
    reader = RegistryReader()
    reader.get_installed_programs()
    program = reader.get_program_by_name(program_name)

    if not program:
        matches = reader.search_programs(program_name)
        if not matches:
            click.echo(f"Program not found: {program_name}", err=True)
            sys.exit(1)
        elif len(matches) > 1:
            click.echo(f"Multiple programs found matching '{program_name}':")
            for p in matches:
                click.echo(f"  - {p.name}")
            click.echo("\nPlease specify the exact program name.")
            sys.exit(1)
        else:
            program = matches[0]

    # Confirmation
    if not yes:
        click.echo(f"\nProgram to uninstall: {program.name}")
        click.echo(f"Publisher: {program.publisher or 'Unknown'}")
        click.echo(f"Version: {program.version or 'Unknown'}")

        if not click.confirm("\nDo you want to continue?"):
            click.echo("Uninstallation cancelled.")
            sys.exit(0)

    # Create backups
    backup_manager = BackupManager()

    if not no_restore_point:
        click.echo("Creating system restore point...")
        if backup_manager.create_restore_point(f"Before uninstalling {program.name}"):
            click.echo("✓ Restore point created")
        else:
            click.echo("⚠ Failed to create restore point", err=True)
            if not yes and not click.confirm("Continue without restore point?"):
                sys.exit(1)

    if not no_backup and program.registry_key:
        click.echo("Backing up registry key...")
        backup_file = backup_manager.backup_registry_key(
            winreg.HKEY_LOCAL_MACHINE,
            program.registry_key.split("HKEY_LOCAL_MACHINE\\")[1],
            f"{program.name.replace(' ', '_')}"
        )
        if backup_file:
            click.echo(f"✓ Registry backed up to {backup_file}")
        else:
            click.echo("⚠ Failed to backup registry", err=True)

    # Execute uninstaller
    click.echo(f"\nRunning uninstaller for {program.name}...")

    uninstaller = Uninstaller(program)
    result = uninstaller.uninstall(
        silent=silent,
        create_backup=(not no_backup),
        timeout=600
    )

    if result.success:
        click.echo(f"[SUCCESS] Uninstallation completed in {result.duration:.2f}s")
        click.echo(f"Exit code: {result.exit_code}")
    else:
        click.echo(f"[FAILED] Uninstallation failed: {result.error_message}", err=True)
        if not yes and not click.confirm("\nContinue to scan for leftovers anyway?"):
            sys.exit(1)

    # Scan for leftovers
    if not no_scan:
        click.echo("\nScanning for leftover files and registry entries...")
        scanner = LeftoverScanner()
        leftovers = scanner.scan(program)

        if leftovers:
            click.echo(f"\nFound {len(leftovers)} leftover items:")
            scanner.print_summary()

            # Ask to clean
            if yes or click.confirm("\nDo you want to remove these leftovers?"):
                click.echo("\nRemoving leftovers...")
                cleaner = Cleaner(create_backup=(not no_backup))
                clean_result = cleaner.clean(leftovers)
                cleaner.print_result(clean_result)
        else:
            click.echo("[SUCCESS] No leftovers found!")


@cli.command()
def sysinfo():
    """Display system information."""
    print_system_info()


@cli.command()
def privileges():
    """Display current privilege information."""
    print_privilege_info()


@cli.command()
@click.option("--keep-days", default=30, help="Number of days to keep backups")
def cleanup(keep_days):
    """Clean up old backups and logs."""
    logger = get_logger()

    click.echo("Cleaning up old backups and logs...")

    # Clean up backups
    backup_manager = BackupManager()
    deleted_backups = backup_manager.cleanup_old_backups(keep_days)
    click.echo(f"✓ Deleted {deleted_backups} old backup(s)")

    # Clean up logs
    deleted_logs = logger.cleanup_old_logs(keep_days)
    click.echo(f"✓ Deleted {deleted_logs} old log file(s)")

    click.echo("Cleanup completed.")


@cli.command()
def backups():
    """List all available backups."""
    backup_manager = BackupManager()
    backup_list = backup_manager.list_backups()

    if not backup_list:
        click.echo("No backups found.")
        return

    click.echo(f"\nFound {len(backup_list)} backup(s):\n")

    for i, backup in enumerate(backup_list, 1):
        click.echo(f"{i}. Type: {backup['type']}")
        click.echo(f"   Time: {backup['timestamp']}")
        click.echo(f"   Path: {backup['path']}")
        if 'details' in backup:
            click.echo(f"   Details: {backup['details']}")
        click.echo()


@cli.command()
@click.argument("program_name")
@click.option("--files/--no-files", default=True, help="Scan for files and directories")
@click.option("--registry/--no-registry", default=True, help="Scan registry")
@click.option("--shortcuts/--no-shortcuts", default=True, help="Scan shortcuts")
def scan(program_name, files, registry, shortcuts):
    """
    Scan for leftover files and registry entries of a program.

    This can be used to check for leftovers without uninstalling.
    """
    logger = get_logger()
    logger.info(f"Scanning for leftovers of: {program_name}")

    # Find the program
    reader = RegistryReader()
    reader.get_installed_programs()
    program = reader.get_program_by_name(program_name)

    if not program:
        matches = reader.search_programs(program_name)
        if not matches:
            click.echo(f"Program not found: {program_name}", err=True)
            sys.exit(1)
        elif len(matches) > 1:
            click.echo(f"Multiple programs found matching '{program_name}':")
            for p in matches:
                click.echo(f"  - {p.name}")
            click.echo("\nPlease specify the exact program name.")
            sys.exit(1)
        else:
            program = matches[0]

    click.echo(f"Scanning for leftovers of: {program.name}")

    scanner = LeftoverScanner()
    leftovers = scanner.scan(
        program,
        scan_files=files,
        scan_registry=registry,
        scan_shortcuts=shortcuts
    )

    if leftovers:
        scanner.print_summary()

        # List some items
        click.echo(f"\nFirst 20 items:")
        for i, leftover in enumerate(leftovers[:20], 1):
            click.echo(f"{i}. {leftover}")

        if len(leftovers) > 20:
            click.echo(f"... and {len(leftovers) - 20} more items")
    else:
        click.echo("No leftovers found.")


@cli.command()
@click.argument("program_name")
@click.option("--no-backup", is_flag=True, help="Skip creating backups")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
def clean(program_name, no_backup, yes):
    """
    Remove leftover files and registry entries of a program.

    This can be used after manual uninstallation to clean up leftovers.
    """
    logger = get_logger()

    # Check for admin privileges
    if not is_admin():
        click.echo("[WARNING] Administrator privileges recommended for cleaning.", err=True)
        if not yes and not click.confirm("Continue anyway?"):
            sys.exit(1)

    logger.info(f"Cleaning leftovers of: {program_name}")

    # Find the program (or search for it)
    reader = RegistryReader()
    reader.get_installed_programs()
    program = reader.get_program_by_name(program_name)

    if not program:
        matches = reader.search_programs(program_name)
        if matches:
            if len(matches) == 1:
                program = matches[0]
            else:
                click.echo(f"Multiple programs found matching '{program_name}':")
                for p in matches:
                    click.echo(f"  - {p.name}")
                click.echo("\nPlease specify the exact program name.")
                sys.exit(1)
        else:
            # Program not found in registry - might be already uninstalled
            # Create a minimal InstalledProgram object for scanning
            from core.registry import InstalledProgram
            program = InstalledProgram(name=program_name)
            click.echo(f"[INFO] Program not found in registry. Searching for leftovers by name: {program_name}")

    # Scan for leftovers
    click.echo(f"Scanning for leftovers of: {program.name}")
    scanner = LeftoverScanner()
    leftovers = scanner.scan(program)

    if not leftovers:
        click.echo("No leftovers found.")
        return

    scanner.print_summary()

    # Confirmation
    if not yes:
        click.echo(f"\nFirst 10 items to be deleted:")
        for i, leftover in enumerate(leftovers[:10], 1):
            click.echo(f"{i}. {leftover}")
        if len(leftovers) > 10:
            click.echo(f"... and {len(leftovers) - 10} more items")

        if not click.confirm(f"\nDo you want to delete these {len(leftovers)} items?"):
            click.echo("Cleaning cancelled.")
            return

    # Clean leftovers
    click.echo("\nRemoving leftovers...")
    cleaner = Cleaner(create_backup=(not no_backup))
    result = cleaner.clean(leftovers)
    cleaner.print_result(result)


if __name__ == "__main__":
    cli()
