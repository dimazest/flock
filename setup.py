from setuptools import setup, find_packages


setup(
    name='flock',
    version='0.1a0',
    description='A tweet analysis project.',
    long_description='',
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3',
    ],
    keywords='',
    author='Dmitrijs Milajevs',
    author_email='dimazest@gmail.com',
    url='https://github.com/dimazest/flock',
    license='MIT license',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'click',
        'click-log',
        'poultry',
        'psycopg2',
        'sqlalchemy',
    ],
    entry_points={
        'console_scripts': [
            'flock = flock.__main__:cli',
        ],
    },
)
