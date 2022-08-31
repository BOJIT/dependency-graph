# dependency_graph

A python script to mapshow the `#include` dependency of C/C++ files.

Based on code in [this repository](https://github.com/pvigier/dependency-graph)

## Installation

The script depends on [Graphviz](https://www.graphviz.org/) to draw the graph.
This script has not been tested on Windows: use Linux or WSL to generate images.

On Ubuntu, you can install the dependencies with these two commands:

```bash
sudo apt install graphviz

# Install Python dependencies
pip3 install -r requirements.txt
# OR... if you use Pipenv
pipenv install
```

## Create Graph

The graph is labelled with the `git-describe` metadata and a timestamp.
Generated images appear in the `img/` directory.
Pass the format flag to specify output image format.

```bash
# If using Pipenv...
pipenv run python dependency_graph.py -f svg

# ...else
python dependency_graph.py -f svg
```

A _red_ arrow indicates inclusion in the _header_ file (public).
A _blue_ arrow indicates inclusion in the _source_ file (private).
