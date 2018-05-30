from setuptools import setup, find_packages


setup(
    name='flock-web',
    version='0.1a0',
    description='The web interface for flock, a tweet analysis project.',
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
    license='Government Legal',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'click',
        'click-log',
        'poultry',
        'sqlalchemy',
        'crosstab',
        'flock',
        'flock-conf',
        'flask',
        'Flask-SQLAlchemy',
        'flask-iniconfig',
        'Flask-Humanize',
        'flask-debugtoolbar',
        'paginate_sqlalchemy',
        'celery',
        'flask-login',
        'WTForms',
        'flask_wtf',
        'scikit-learn',
        'pandas',
    ],
    entry_points={
        'console_scripts': [
            'flock-web = flock_web.__main__:cli',
        ],
    },
)
