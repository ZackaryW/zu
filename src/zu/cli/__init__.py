import datetime
from functools import cache
import os
import platform
import click
import toml
import zu.cli.__enum__ as ZU_ENUM
import json
import sys
from zu.cli.utils import robust_remove_directory
import subprocess

def pkg_exist(pkg_name):
    if os.path.exists(os.path.join(ZU_ENUM.ZU_GLOBAL_REPO_STORE, pkg_name)):
        return True
    if os.path.exists(os.path.join(ZU_ENUM.ZU_UTIL_PKG_STORE, pkg_name)):
        return True
    return False

def pkg_iter():
    for pkg in os.listdir(ZU_ENUM.ZU_GLOBAL_REPO_STORE):
        if os.path.isfile(os.path.join(ZU_ENUM.ZU_GLOBAL_REPO_STORE, pkg)):
            continue
        if pkg.startswith(".") or pkg.startswith("__"):
            continue
        yield pkg, os.path.join(ZU_ENUM.ZU_GLOBAL_REPO_STORE, pkg)
    for pkg in os.listdir(ZU_ENUM.ZU_UTIL_PKG_STORE):
        if os.path.isfile(os.path.join(ZU_ENUM.ZU_UTIL_PKG_STORE, pkg)):
            continue
        if pkg.startswith(".") or pkg.startswith("__"):
            continue
        yield pkg, os.path.join(ZU_ENUM.ZU_UTIL_PKG_STORE, pkg)

def pkg_install(pkg_name, _global : bool = False):
    
    if _global:
        os.system(f"git clone {ZU_ENUM.PKG_GIT_URL.format(pkg_name=pkg_name)} {os.path.join(ZU_ENUM.ZU_GLOBAL_REPO_STORE, pkg_name)}")
    else:
        os.system(f"git clone {ZU_ENUM.PKG_GIT_URL.format(pkg_name=pkg_name)} {os.path.join(ZU_ENUM.ZU_UTIL_PKG_STORE, pkg_name)}")


@cache
def get_pkg_record():
    try:
        with open(ZU_ENUM.ZU_REPO_UPDATE_RECORD, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def update_pkg_record(pkg_name, pkg_time):
    record = get_pkg_record()
    record[pkg_name] = pkg_time
    with open(ZU_ENUM.ZU_REPO_UPDATE_RECORD, "w") as f:
        json.dump(record, f)

@cache
def get_index():
    """Get the package index"""
    index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "indexes.json")
    try:
        with open(index_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def check_pkg_in_index(pkg_name: str) -> bool:
    """Check if a package exists in the index"""
    index = get_index()
    return any(pkg['repository'] == pkg_name for pkg in index)

def check_pkg_exists(pkg_name):
    if pkg_exist(pkg_name):
        return True, os.pathpath.join(ZU_ENUM.ZU_GLOBAL_REPO_STORE, pkg_name) if pkg_name.startswith(ZU_ENUM.ZU_GLOBAL_REPO_STORE) else (False, os.path.join(ZU_ENUM.ZU_UTIL_PKG_STORE, pkg_name))
    return False, None

def pkg_update(pkg_name, _global : bool = False, force : bool = False):
    if pkg_name == "zu":
        run_detached(["pip", "install", "-U", "git+https://github.com/ZackaryW/zu.git"])
        sys.exit()
    
    if not check_pkg_in_index(pkg_name):
        click.echo(f"Package {pkg_name} does not exist in index", color="red")
        return

    exists, _ = check_pkg_exists(pkg_name)
    if not exists:
        click.echo(f"Package {pkg_name} does not exist locally")
        return

    if not force:
        pkg_time = get_pkg_record().get(pkg_name, 0)
        if (now := datetime.datetime.now()) - datetime.datetime.fromtimestamp(pkg_time) < datetime.timedelta(days=1):
            click.echo(f"Package {pkg_name} is still fresh", color="green")
            return

        update_pkg_record(pkg_name, now.timestamp())

    old_cd = os.getcwd()
    if _global:
        os.chdir(os.path.join(ZU_ENUM.ZU_GLOBAL_REPO_STORE, pkg_name))
    else:
        os.chdir(os.path.join(ZU_ENUM.ZU_UTIL_PKG_STORE, pkg_name))

    os.system("git pull")

    os.chdir(old_cd)

def pkg_list():
    pkg_stats = {}
    for pkg, path in pkg_iter():
        pkg_version = toml.load(os.path.join(path, "pyproject.toml"))["project"]["version"]
        pkg_stats[pkg] = {
            "name": pkg,
            "version": pkg_version,
            "path": path,
            "global": path.startswith(ZU_ENUM.ZU_GLOBAL_REPO_STORE)
        }
    return pkg_stats


@click.group(invoke_without_command=True)
@click.pass_context
def zu(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("use 'zu kv' for key-value store")
        click.echo("use 'zu <pkg>' to run pkg directly")
        click.echo(ctx.get_help())


@zu.command()
@click.argument("pkg_name")
@click.option("-u", "--update", is_flag=True)
@click.option("-g", "--to-global", is_flag=True)
def get(pkg_name, update, to_global):
    if pkg_name == "zu":
        pkg_update(pkg_name, to_global, update)
        sys.exit()

    if not check_pkg_in_index(pkg_name):
        click.echo(f"Package {pkg_name} does not exist in index", color="red")
        return

    exists, _ = check_pkg_exists(pkg_name)
    if not exists:
        click.echo(f"Package {pkg_name} does not exist locally")
        pkg_install(pkg_name, to_global)
        click.echo(f"Package {pkg_name} installed", color="green")
    elif update:
        pkg_update(pkg_name, to_global, True)
    else:
        click.echo(f"Package {pkg_name} is already installed", color="yellow")
        pkg_update(pkg_name, to_global)
        return

@zu.command()
def list():
    for name, pkg in pkg_list().items():
        click.echo(f"{name}\t\t{pkg['version']} {" g" if pkg['global'] else ""}")

@zu.command()
@click.argument("pkg_name")
@click.option("-g", "--to-global", is_flag=True)
@click.option("-f", "--force", is_flag=True, help="Force removal even if files are locked")
def remove(pkg_name, to_global, force):
    if not check_pkg_in_index(pkg_name):
        click.echo(f"Package {pkg_name} does not exist in index", color="red")
        return

    exists, path = check_pkg_exists(pkg_name)
    if not exists:
        click.echo(f"Package {pkg_name} does not exist locally")
        return
    
    if robust_remove_directory(path):
        click.echo(f"Package {pkg_name} removed", color="green")
    else:
        click.echo(f"Failed to remove package {pkg_name}: Permission denied", color="red")
        click.echo("Try using --force option or close any programs that might be using the package files")

@zu.command()
@click.option("-g", "--to-global", is_flag=True)
def purge(to_global):
    if to_global:
        robust_remove_directory(ZU_ENUM.ZU_GLOBAL_REPO_STORE)

    robust_remove_directory(ZU_ENUM.ZU_UTIL_PKG_STORE)

@zu.command()
def index():
    index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "indexes.json")
    with open(index_path, "r") as f:
        index = json.load(f)

    listed = pkg_list()
    for pkg in index:
        click.echo(f"{pkg['repository']}\t\t{pkg['version']} {f"=> {listed[pkg['repository']]['version']} " if pkg['repository'] in listed else "not installed"}")

def run_detached(cmd, pkg_path=None):
    # On Windows, use DETACHED_PROCESS flag
    if platform.system() == "Windows":
        subprocess.Popen(cmd, cwd=pkg_path, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    # On Unix-like systems, use nohup
    else:
        subprocess.Popen(["nohup"] + cmd, cwd=pkg_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def run_package(pkg_path: str, pkg_name: str):
    """Run a package with rye sync and proper argument handling"""
    try:
        subprocess.run(["rye", "sync"], cwd=pkg_path, check=True)
        cmd = ["rye", "run", f"zu-{pkg_name}"]
        if len(sys.argv) > 2:
            cmd.extend(sys.argv[2:])
        
        if run_as_detached:
            run_detached(cmd, pkg_path)
        else:
            subprocess.run(cmd, cwd=pkg_path, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

def zu_entry():
    if "-g" in sys.argv or "--to-global" in sys.argv:
        if platform.system() == "Windows":
            import pyuac
            if not pyuac.isUserAdmin():
                click.echo("Please run as admin")
                sys.exit(1)
        else:
            os.execvp("sudo", ["sudo"] + sys.argv)
            sys.exit()  
            
    global run_as_detached
    run_as_detached = False

    if len(sys.argv) == 1:
        zu()

    elif sys.argv[1] == "-d":
        sys.argv.pop(1)
        run_as_detached = True

    elif sys.argv[1] in ZU_ENUM.ZU_INTERNAL_COMMANDS:
        zu()
    elif sys.argv[1] == "kv":
        sys.argv = sys.argv[1:]
        from zu.cli.kv import kv
        kv()
    elif os.path.exists(pkg_path := os.path.join(ZU_ENUM.ZU_GLOBAL_REPO_STORE, sys.argv[1])):
        run_package(pkg_path, sys.argv[1])
    elif os.path.exists(pkg_path := os.path.join(ZU_ENUM.ZU_UTIL_PKG_STORE, sys.argv[1])):
        run_package(pkg_path, sys.argv[1])
    else:
        click.echo(f"Command {sys.argv[1]} not found")


if __name__ == "__main__":
    zu_entry()

