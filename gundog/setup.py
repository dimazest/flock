from setuptools import setup, find_packages


setup(
    name='gundog',
    version='0.1a0',
    description='A baseline real-time tweet retrieval system.',
    long_description='',
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3',
    ],
    keywords='',
    author='Dmitrijs Milajevs',
    author_email='dimazest@gmail.com',
    url='https://github.com/dimazest/flock',
    license='Public Domain',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'click',
        'click-log',
        'numpy',
        'pyzmq',
    ],
    entry_points={
        'console_scripts': [
            'gundog = gundog.__main__:cli',
        ],
    },
)
