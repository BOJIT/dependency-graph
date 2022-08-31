# @file dependency_graph.py
# @author James Bennion-Pedley
# @brief CLI tool for analysing dependencies in C/C++ projects
# @date 31/08/2022
#
# @copyright Copyright (c) 2022

__version__ = "1.0.0"

#---------------------------------- Imports -----------------------------------#

# Built-in
import os
import re
import argparse
import pprint
import codecs
from collections import defaultdict
from datetime import datetime

# PYPI
from graphviz import Digraph
import git

#---------------------------------- Helpers -----------------------------------#

def filename_normalize(path):
    """
    Return the name of the node that will represent the file at path.
    """

    filename = os.path.basename(path)
    end = filename.rfind('.')
    end = end if end != -1 else len(filename)
    return filename[:end]


def filename_extension(path):
    """
    Return the extension of the file targeted by path.
    """

    return path[path.rfind('.'):]

#-------------------------------- Primary Class -------------------------------#

class DependencyGraph():

    #------------------------------- Properties -------------------------------#

    # Default blacklist relative to root directory. More can be added with CLI
    base_blacklist = [
        ".git",
        ".settings",
        ".vscode",
    ]

    # Module groups
    base_groups = [

    ]

    # Syntax of C/C++ include statement
    include_regex = re.compile('#include\s+["<"](.*)[">]')

    # Default path of images
    output_path = './img/'

    # Extensions for files
    valid_headers = [['.h', '.hpp'], 'red']
    valid_sources = [['.c', '.cc', '.cpp'], 'blue']
    valid_extensions = valid_headers[0] + valid_sources[0]

    #------------------------------- Lifecycle --------------------------------#

    def __init__(self, root='.'):
        self._root = root
        self.blacklist = list(map(lambda f: os.path.join(self._root, f), self.base_blacklist))
        self.groups = list(map(lambda f: os.path.join(self._root, f), self.base_groups))

    def __del__(self):
        pass

    #-------------------------------- Private ---------------------------------#

    def auto_name(self):
        """
        Generate automatic name for output file based on project metadata
        """

        ts = datetime.now().strftime("%d-%m-%Y %H.%M.%S")

        # Are we in a Git repo?
        try:
            g = git.Repo(self._root)
        except Exception as e:
            return f"local - {ts}"

        # Do we have a tag description?
        try:
            id = git.cmd.Git(self._root).describe(tags=True)
        except Exception as e:
            long_id = g.head.commit.hexsha
            id = g.git.rev_parse(long_id, short=6)

        # Is the repo dirty?
        if g.is_dirty():
            ts = datetime.now().strftime("%d-%m-%Y %H.%M.%S")
            return id + " - " + ts
        else:
            return id

    def find_files(self, path, recursive=True):
        """
        Return a list of all the files in the folder.
        If recursive is True, the function will search recursively.
        """

        files = []
        for entry in os.scandir(path):
            if entry.is_dir() and recursive:
                if(entry.path not in self.blacklist):
                    files += self.find_files(entry.path)
            elif filename_extension(entry.path) in self.valid_extensions:
                files.append(entry.path)

        return files

    def find_neighbors(self, path):
        """
        Find all the other nodes included by the file targeted by path.
        """

        f = codecs.open(path, 'r', "utf-8", "ignore")
        code = f.read()
        f.close()
        return [filename_normalize(include) for include in self.include_regex.findall(code)]


    #-------------------------------- Public ----------------------------------#

    def create_graph(self, files, strict):
        """
        Create a graph from a list of source files
        """

        # Create graph
        graph = Digraph(strict=strict, node_attr={'color': 'lightblue2', 'style': 'filled'})

        # Find nodes and groups
        nodes = set()
        proxy_nodes = {}

        folder_to_files = defaultdict(list)
        for path in files:
            folder_to_files[os.path.dirname(path)].append(path)

            in_group = False
            for group in self.groups:
                if path.startswith(group):
                    group_name = f"group - {filename_normalize(group)}"
                    nodes.add(group_name)
                    graph.node(group_name, _attributes={'color': 'lightgreen'})
                    proxy_nodes[filename_normalize(path)] = group_name
                    in_group = True

            if not in_group:
                nodes.add(filename_normalize(path))

        # Find edges
        for folder in folder_to_files:

            in_group = False
            for group in self.groups:
                if folder.startswith(group):
                    in_group = True

            if not in_group:
                for path in folder_to_files[folder]:
                    color = 'black'
                    node = filename_normalize(path)
                    ext = filename_extension(path)
                    if ext in self.valid_headers[0]:
                        color = self.valid_headers[1]
                    if ext in self.valid_sources[0]:
                        color = self.valid_sources[1]

                    graph.node(node)

                    neighbors = self.find_neighbors(path)
                    for neighbor in neighbors:
                        if neighbor != node:
                            if neighbor in nodes:
                                graph.edge(node, neighbor, dir="back", color=color)
                            elif neighbor in proxy_nodes:
                                graph.edge(node, proxy_nodes[neighbor], dir="back", color=color)

        return graph

    def run(self, args):
        # If blacklist is provided, append new entries
        added_blacklist = [item for sublist in args['blacklist'] for item in sublist]
        self.base_blacklist += added_blacklist
        self.blacklist = list(map(lambda f: os.path.join(self._root, f), self.base_blacklist))

        # If group is provided, append new entries
        added_groups = [item for sublist in args['group'] for item in sublist]
        self.base_groups += added_groups
        self.groups = list(map(lambda f: os.path.join(self._root, f), self.base_groups))

        print(self.groups)

        # Get all target files
        files = self.find_files(self._root)

        print("FileList:")
        print("--------------------------------------")
        pprint.pprint(files)
        print("--------------------------------------")

        print("Parsing files ...")

        graph = self.create_graph(files, args['strict'])
        graph.format = args['format']

        print("--------------------------------------")

        # Choose output directory
        if args['output'] != None:
            img_path = args['output']
        else:
            img_path = self.output_path + self.auto_name()


        print(f"Rendering Graph to {img_path}.{args['format']} ...")
        graph.render(img_path, cleanup=True)

        print("--------------------------------------")
        print("Done!")


#------------------------------------ CLI -------------------------------------#

def main(argv=None):
    parser = argparse.ArgumentParser(description=f"{__file__} v{__version__} - \
        Command-line tool for visualising C/C++ #include dependencies", prog=f"{__file__}")

    # Core positional argument = source code root
    parser.add_argument('root', type=str, help="Root of project directory")

    # Add optional configuration
    parser.add_argument('-f', '--format', help='Format of the output file', default='svg',
        choices=['bmp', 'gif', 'jpg', 'png', 'pdf', 'svg'])
    parser.add_argument('-s', '--strict', action='store_true',
        help='Rendering should merge multi-edges', default=False)
    parser.add_argument('-o', '--output', type=str,
        help='Name of output file - defaults to auto-naming scheme', default=None)
    parser.add_argument('-b', '--blacklist', action='append', nargs='+',
        help='Blacklisted directories. Relative to root directory', default=[])
    parser.add_argument('-g', '--group', action='append', nargs='+',
        help='Directories to consider as single nodes. Relative to root directory', default=[])

    # Parse commands and convert to standard Python arguments
    nsargs = parser.parse_args()
    args = vars(nsargs)

    # Create class and run instance
    dg = DependencyGraph(root=args['root'])
    dg.run(args)   # Only one default command in this CLI tool

#--------------------------------- Entry Point --------------------------------#

if __name__ == '__main__':
    main()
