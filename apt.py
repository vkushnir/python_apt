#!/usr/bin/env python3.10

# https://wiki.debian.org/DebianRepository/Format

import argparse
import configparser
import gzip
import logging
import os
import platform
import posixpath
import re
import sqlite3
import sys
from urllib.parse import urljoin

import requests
from colorama import Fore, Style

_version_ = '0.2'


def get_arguments(args=None):
    """Get arguments from the command line."""
    # Argument parser basic configuration
    parser = argparse.ArgumentParser(
        description='Apt package downloader.', epilog='Example: apt.py -p vim -p nano --info --deps')
    parser.add_argument('--version', action='version', version=f'%(prog)s {_version_}')
    
    # Argument parser groups
    sys_options = parser.add_argument_group(title='system options',
                                            description='Properties of the system for which packages will be chosen.')
    apt_actions = parser.add_argument_group(title='apt actions',
                                            description='Actions to be performed with the selected options.')
    p_parameters = parser.add_argument_group(title='package parameters',
                                             description='Packages or file names to search/download.')
    
    # Argument parser basic options
    parser.add_argument('--cache', dest='apt_cache', default='.cache.db',
                        help='Package index cache file path.')
    parser.add_argument('--sources', dest='apt_sources', default='sources.list',
                        help='Apt "sources.list" file path.')
    parser.add_argument('--repo', dest='apt_repo',
                        help='Repository url.')
    parser.add_argument('--dir', dest='apt_download', default='.',
                        help='Download directory.')
    # Argument parser system options
    sys_options.add_argument('-i', '--id', dest='sys_id', default=get_distro()['id'],
                             help='System ID. (eg. ubuntu, debian)')
    sys_options.add_argument('-t', '--type', dest='sys_type', default='deb',
                             help='Package type. (eg. deb, deb-src)')
    sys_options.add_argument('-d', '--distro', dest='sys_distro', default=get_distro()['codename'],
                             help='Distribution code name. (eg. focal, buster)')
    sys_options.add_argument('-c', '--comp', dest='sys_component', default='main',
                             help='Component. (eg. main, universe)')
    sys_options.add_argument('-a', '--arch', dest='sys_arch', default=platform.machine(),
                             help='Platform architecture. (eg. amd64, arm64)')
    # Argument parser apt actions
    apt_actions.add_argument('--update', dest='update', action='store_true',
                             help='Update the package index cache.')
    apt_actions.add_argument('--info', dest='get_info', action='store_true',
                             help='Show package information about specified packages.')
    apt_actions.add_argument('--deps', dest='with_dependencies', action='store_true',
                             help='Download with dependencies.')
    apt_actions.add_argument('--download', dest='download', action='store_true',
                             help='Download specified packages.')
    # Argument parser package parameters
    p_parameters.add_argument('-p', '--package', dest='packages', action='append',
                              help='Package names.')
    p_parameters.add_argument('-f', '--file', dest='files', action='append',
                              help='File names.')
    
    return parser.parse_args(args)


# TODO: add support for .env file with system options
# TODO: add more system detection methods


def get_packages_stream(s):
    """Return a generator that yields packages from a stream."""
    package = {}
    previous_key = None
    for line in s.splitlines():
        if line == '':
            yield package
            package = {}
            previous_key = None
        elif line.startswith(' '):
            package[previous_key] += line.strip()
        else:
            key, value = line.split(':', 1)
            package[key.strip()] = value.strip()
            previous_key = key
    yield package


def get_distro():
    """Get the distribution code name."""
    if platform.system() == 'Linux':
        if os.path.isfile('/etc/os-release'):
            config = configparser.ConfigParser()
            config.read('/etc/os-release')
            return dict(id=config['ID'],
                        name=config['NAME'],
                        version=config['VERSION_ID'],
                        codename=config['VERSION_CODENAME'])
    else:
        logging.warning('Unsupported operating system.')
        return dict(id='*', name='*', version='*', codename='*')


def get_package_index_url(url, distro, component, arch):
    """Get the package index url.
    :type url: str The repository url.
    :type distro: str The distribution code name.
    :type component: str The component.
    :type arch: str The architecture.
    dists/$DIST/$COMP/binary-$ARCH/Packages.gz
    """
    return urljoin(url, posixpath.join('dists', distro, component, f'binary-{arch}', 'Packages.gz'))


def get_package_content_url(url, distro, component, arch):
    """Get the package index url.
    :type url: str The repository url.
    :type distro: str The distribution code name.
    :type component: str The component.
    :type arch: str The architecture.
    dists/$DIST/$COMP/Contents-$SARCH.gz
    """
    return urljoin(url, posixpath.join('dists', distro, component, f'Contents-{arch}.gz'))


def get_repo_url(opts):
    """Get the repository url.
    :type opts: dict The options.
    """
    if opts.apt_repo:
        return opts.apt_repo
    else:
        with (open(opts.apt_sources, 'r') as f):
            lines = f.readlines()
            for line in lines:
                if line.startswith(f'{opts.sys_type} '):
                    components = line.rstrip().split(' ')
                    if len(components) < 4:
                        continue
                    if components[2].upper() == opts.sys_distro.upper() \
                            and components[3].upper() == opts.sys_component.upper():
                        return components[1]
        logging.error('Cannot find repository url.')
        sys.exit(1)


def get_repos(opts):
    """Get list of repositories.
    :type opts: Namespace The options.
    :rtype: list of objects The list of repositories.
    """
    repos = []
    with (open(opts.apt_sources, 'r') as f):
        lines = f.readlines()
        for line in lines:
            if line.startswith(f'{opts.sys_type} '):
                components = line.rstrip().split(' ')
                if len(components) < 4:
                    continue
                repos.append(dict(
                    type=components[0],
                    url=components[1],
                    distro=components[2],
                    component=components[3]))
    if opts.apt_repo:
        repos.append(dict(
            type=opts.sys_type,
            url=opts.apt_repo,
            distro=opts.sys_distro,
            component=opts.sys_component))
    return repos


def get_connection(opts):
    """Get the database connection. (create all tables if not exists)
    :type opts: Namespace() The options.
    """
    conn = sqlite3.connect(opts.apt_cache)
    cur = conn.cursor()
    # Repo table format: id, os, type, distro, component, url
    cur.execute('CREATE TABLE IF NOT EXISTS repos ('
                'id INTEGER PRIMARY KEY, '
                'os TEXT, '
                'type TEXT, '
                'distro TEXT, '
                'component TEXT, '
                'url TEXT)')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS repo_idx ON repos (os, type, distro, component, url)')
    
    # Packages table format: id, repo_id, package, filename, version, arch, depends, pre_depends, description,
    # section, priority, size
    cur.execute('CREATE TABLE IF NOT EXISTS packages ('
                'id INTEGER PRIMARY KEY, '
                'repo_id INTEGER, '
                'package TEXT, '
                'filename TEXT, '
                'version TEXT, '
                'arch TEXT, '
                'depends TEXT, '
                'pre_depends TEXT, '
                'description TEXT, '
                'section TEXT, '
                'priority TEXT, '
                'size INTEGER)')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS package_idx ON packages (repo_id, package, version, arch)')
    
    # Contents table format: id, repo_id, file, package, arch
    cur.execute('CREATE TABLE IF NOT EXISTS contents ('
                'id INTEGER PRIMARY KEY, '
                'repo_id INTEGER, '
                'file TEXT, '
                'location TEXT, '
                'arch TEXT)')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS contents_idx ON contents (repo_id, file, location, arch)')
    conn.commit()
    cur.close()
    return conn


def download_file(url, filename=None):
    """Get a file from the web.
    :type url: str The url.
    :type filename: str The filename.
    """
    if filename:
        print(
            f'{Style.DIM}Downloading{Style.NORMAL} {Fore.GREEN}{url}{Fore.RESET} '
            f'{Style.DIM}to{Style.NORMAL} {Fore.CYAN}{filename} {Style.DIM}...{Style.RESET_ALL}')
        r = requests.get(url, allow_redirects=True)
        open(filename, 'wb').write(r.content)
        return filename
    else:
        print(f'{Style.DIM}Downloading{Style.NORMAL} {Fore.GREEN}{url}{Fore.RESET} {Style.DIM}...{Style.RESET_ALL}')
        response = requests.get(url, allow_redirects=True)
        if response.status_code != 200:
            logging.error(f'Cannot download {url}, status code: {response.status_code}')
            return None
        # check if the content is compressed
        if response.content[:2] == b'\x1f\x8b':
            return gzip.decompress(response.content).decode('utf-8')
        else:
            return response.content.decode('utf-8')


def update_cache(opts, repos, conn):
    """Update the package index cache.
    :type opts: Namespace The options.
    :type repos: list of objects The list of repositories.
    :type conn: Connection The database connection.
    """
    cur = conn.cursor()
    for repo in repos:
        # add repo to the database if it doesn't exist and get the id
        cur.execute('INSERT OR IGNORE INTO repos (os, type, distro, component, url) values (?, ?, ?, ?, ?)',
                    (opts.sys_id, repo['type'], repo['distro'], repo['component'], repo['url']))
        cur.execute('SELECT id FROM repos WHERE os=? AND type=? AND distro=? AND component=? AND url=?',
                    (opts.sys_id, repo['type'], repo['distro'], repo['component'], repo['url']))
        repo_id = cur.fetchone()[0]
        logging.info(f'Updating {repo["url"]}, {repo["distro"]}, {repo["component"]}')
        # download the package index
        index = download_file(get_package_index_url(repo['url'], repo['distro'], repo['component'], opts.sys_arch))
        if index is None:
            continue
        packages = get_packages_stream(index)
        for package in packages:
            cur.execute('INSERT OR IGNORE INTO packages (repo_id, package, filename, version, arch, depends, '
                        'pre_depends, description, section, priority, size) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (repo_id, package.get('Package', None), package.get('Filename', None),
                         package.get('Version', None), package.get('Architecture', None),
                         package.get('Depends', None), package.get('Pre-Depends', None),
                         package.get('Description', None), package.get('Section', None),
                         package.get('Priority', None), package.get('Size', None)))
        # download the contents index
        contents = download_file(get_package_content_url(repo['url'], repo['distro'], repo['component'], opts.sys_arch))
        if contents is None:
            continue
        for line in contents.splitlines():
            fl = line.split()
            cur.execute('INSERT OR IGNORE INTO contents (repo_id, file, location, arch) values (?, ?, ?, ?)',
                        (repo_id, fl[0], fl[1], opts.sys_arch))
    conn.commit()
    cur.close()


def get_dependencies(opts, conn, dependencies):
    """Get package dependencies."""
    depends_re = re.compile(
        r'^(?P<package>[a-zA-Z0-9\-+.]+)(?:\s+\((?P<condition>[>=<~]+)?\s+(?P<version>[0-9a-z.:\-+~]+)\))?')
    logging.debug(f'Getting dependencies packages {dependencies}')
    depends = [depends_re.search(depend.strip(), 0).groupdict() for depend in dependencies.split(',')]
    deps_packages = get_packages(opts, conn, [depend['package'] for depend in depends])
    [deps_packages.update(get_dependencies(opts, conn, deps['depends']))
     for deps in deps_packages.values() if deps['depends'] and deps['package'] not in deps_packages]
    return deps_packages


def get_packages(opts, conn, packages, like=False):
    """Get packages from the package index cache."""
    results = {}
    cur = conn.cursor()
    for package in packages:
        if like:
            cur.execute('SELECT p.package, p.version, p.filename, p.arch, p.depends, p.section, p.description, '
                        'r.type, r.distro, r.component, r.url '
                        'FROM packages p, repos r '
                        'WHERE r.id=p.repo_id '
                        'AND r.os=? AND r.type=? AND r.distro=? AND r.component=? AND p.arch=? '
                        'AND p.package LIKE ?',
                        (opts.sys_id,
                         opts.sys_type,
                         opts.sys_distro,
                         opts.sys_component,
                         opts.sys_arch,
                         f'%{package}%'))
        else:
            cur.execute('SELECT p.package, p.version, p.filename, p.arch, p.depends, p.section, p.description, '
                        'r.type, r.distro, r.component, r.url '
                        'FROM packages p, repos r '
                        'WHERE r.id=p.repo_id '
                        'AND r.os=? AND r.type=? AND r.distro=? AND r.component=? AND p.arch=? '
                        'AND p.package=?',
                        (opts.sys_id,
                         opts.sys_type,
                         opts.sys_distro,
                         opts.sys_component,
                         opts.sys_arch, package))
        rows = cur.fetchall()
        for row in rows:
            data = {}
            [data.update({k: v}) for k, v in zip([d[0] for d in cur.description], row)]
            results.update({data['package']: data})
    cur.close()
    return results


def update(opts, conn):
    """Update the package index."""
    repos = get_repos(opts)
    update_cache(opts, repos, conn)


def search_files(opts, conn):
    """Search for files in the contents index cache."""
    cur = conn.cursor()
    for file in opts.files:
        cur.execute('SELECT c.file, c.location FROM contents c '
                    'WHERE c.arch=? AND c.file LIKE ?',
                    (opts.sys_arch, f'%{file}%'))
        rows = cur.fetchall()
        print(f'\n{Style.BRIGHT}{Fore.YELLOW}Found {len(rows)} files for "{file}".{Fore.RESET}{Style.NORMAL}')
        for row in rows:
            data = {}
            [data.update({k: v}) for k, v in zip([d[0] for d in cur.description], row)]
            print(
                f'{Style.DIM}File:{Style.NORMAL} {Fore.GREEN}{data["file"]}{Fore.RESET}{Style.DIM}, '
                f'Package: {Style.RESET_ALL}{Fore.YELLOW}{data["location"]}{Fore.RESET}')
    cur.close()


def show_packages(opts, conn):
    """Search for packages in the package index cache."""
    for package in opts.packages:
        packages = get_packages(opts, conn, [package], like=True)
        print(f'\n{Style.BRIGHT}{Fore.YELLOW}Found {len(packages)} packages for "{package}".{Fore.RESET}{Style.NORMAL}')
        [print(f'{Style.DIM}Package:{Style.NORMAL} {Fore.GREEN}{data["package"]}{Fore.RESET}, '
               f'{Style.DIM}Description:{Style.NORMAL} {Fore.CYAN}{data["description"]}{Fore.RESET}') for data in
         packages.values()]


def show_package_info(opts, conn):
    """Show package information."""
    packages = get_packages(opts, conn, opts.packages)
    for _, package in packages.items():
        print(f'\nPackage: {Fore.GREEN}{Style.BRIGHT}{package["package"]}{Fore.RESET}:')
        [print(f'  {Style.DIM}{k}:{Style.NORMAL} {Fore.YELLOW}{v}{Style.RESET_ALL}')
         for k, v in package.items() if k not in ['package', 'type', 'distro', 'component', 'url']]
        if opts.with_dependencies and len(package['depends']) > 0:
            dependencies = get_dependencies(opts, conn, package['depends'])
            print(f'    {Style.DIM}From {Style.NORMAL}{len(package["depends"].split(","))}{Style.DIM} dependencies, '
                  f'found {Style.NORMAL}{len(dependencies)}{Style.RESET_ALL}')
            [print(f'      {Style.DIM}package :{Style.NORMAL} {Fore.YELLOW}{depend["package"]}{Style.RESET_ALL}') for
             depend in dependencies.values()]


def download(opts, conn):
    """Download packages."""
    # download packages
    packages = get_packages(opts, conn, opts.packages)
    print(f'\n{Style.BRIGHT}{Fore.YELLOW}Download {len(packages)} packages.{Fore.RESET}{Style.NORMAL}')
    [download_file(urljoin(package['url'], package['filename']),
                   os.path.join(opts.apt_download, os.path.basename(package['filename'])))
     for package in packages.values()]
    if opts.with_dependencies:
        # download dependencies
        dependencies = {}
        [dependencies.update({dpackage['package']: dpackage})
         for package in packages.values()
         for dpackage in get_dependencies(opts, conn, package['depends']).values()]
        dependencies = {k: v for k, v in dependencies.items() if k not in packages.keys()}
        print(f'\n{Style.BRIGHT}{Fore.YELLOW}Download {len(dependencies)} dependencies.{Fore.RESET}{Style.NORMAL}')
        [download_file(urljoin(dependency['url'], dependency['filename']),
                       os.path.join(opts.apt_download, os.path.basename(dependency['filename'])))
         for dependency in dependencies.values()]


def main(opts):
    """Main function."""
    # Print current system settings
    print(f"{Style.BRIGHT}Current settings{Style.NORMAL}:\n"
          f"        id: {Style.BRIGHT}{opts.sys_id}{Style.NORMAL}\n"
          f"      type: {Style.BRIGHT}{opts.sys_type}{Style.NORMAL}\n"
          f"    distro: {Style.BRIGHT}{opts.sys_distro}{Style.NORMAL}\n"
          f" component: {Style.BRIGHT}{opts.sys_component}{Style.NORMAL}\n"
          f"      arch: {Style.BRIGHT}{opts.sys_arch}{Style.NORMAL}\n"
          f"==================")
    # Check system if all system parameters are set
    if (
            opts.sys_id == '*' or
            opts.sys_type == '*' or
            opts.sys_distro == '*' or
            opts.sys_component == '*' or
            opts.sys_arch == '*'):
        logging.error('Invalid system parameters.')
        sys.exit(1)
    # Proceed with the selected options
    conn = get_connection(opts)
    try:
        if opts.update:
            update(opts, conn)
        if opts.download:
            download(opts, conn)
        else:
            if opts.files:
                search_files(opts, conn)
            if opts.packages:
                if opts.get_info:
                    show_package_info(opts, conn)
                else:
                    show_packages(opts, conn)
    except Exception as e:
        logging.exception(e)
        sys.exit(1)
    finally:
        conn.close()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    """Main entry point."""
    logging.basicConfig(level=logging.WARNING)
    opts = get_arguments()
    main(opts)
