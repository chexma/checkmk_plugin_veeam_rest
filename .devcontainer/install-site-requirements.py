"""Install test helpers into the site Python without shadowing Checkmk's own packages.

Usage (as site user, with the site's python3):
    python3 install-site-requirements.py requirements-site.txt constraints-site.txt

The site's pip3 always installs with --target local/lib/python3, which ignores
installed packages: a plain install would put local copies of requests,
urllib3, pytest, ... in front of the ones Checkmk ships. So the requirements
are installed with --no-deps, and then only the dependencies this Checkmk
version does not ship are added, again with --no-deps, at the versions pinned
in the constraints file. Checkmk 2.4 ships pytest, 2.5 does not: the same
files work for both.
"""

import importlib
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution

from packaging.requirements import Requirement


def pip_install(args):
    subprocess.run(["pip3", "install", "--no-cache-dir", "--no-deps", *args], check=True)
    importlib.invalidate_caches()


def requirement_names(path):
    with open(path) as f:
        lines = (line.split("#")[0].strip() for line in f)
        return [Requirement(line).name for line in lines if line]


def missing_dependencies(names):
    """Requirements of the given distributions that are not installed at all."""
    missing = {}
    for name in names:
        for spec in distribution(name).requires or []:
            req = Requirement(spec)
            if req.marker and not req.marker.evaluate({"extra": ""}):
                continue
            try:
                installed = distribution(req.name).version
            except PackageNotFoundError:
                missing[req.name] = req
                continue
            if req.specifier and not req.specifier.contains(installed, prereleases=True):
                print(f"WARNING: {name} wants {req}, Checkmk has {req.name} {installed}")
    return missing


def main():
    requirements, constraints = sys.argv[1:3]
    pip_install(["-r", requirements])
    todo = requirement_names(requirements)
    added = []
    while todo:
        missing = missing_dependencies(todo)
        if not missing:
            break
        print("Not shipped by Checkmk, installing:", ", ".join(sorted(missing)))
        pip_install(["-c", constraints, *(str(req) for req in missing.values())])
        todo = list(missing)
        added += todo
    print("Added dependencies:", ", ".join(sorted(added)) or "none")


if __name__ == "__main__":
    main()
