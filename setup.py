from setuptools import setup

setup(
    name='babbisch-gccxml',
    version='0.1',
    packages=['babbisch'],

    install_requires=['pygccxml'],

    entry_points={
            'console_scripts': [
                'babbisch-gccxml = babbisch:main',
            ]
    },
    zip_safe=False,
    package_data={
            'babbisch': 'headers',
        },
)
