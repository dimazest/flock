from setuptools import setup, find_packages


entry_points = """
[zc.buildout]
default = flock_conf.recipe:Config
"""

setup(
    name='flock-conf',
    entry_points=entry_points,
    packages=find_packages(),
    install_requires=(
        'zc.buildout',
    )
)
