import setuptools

setuptools.setup(
    name="lojacimport",
    version="0.1",
    description="loj.ac importer to polygon.codeforces.com",
    author="Niyaz Nigmatullin",
    install_requires=[
        'polygon_client>=1.0a6',
        'requests',
        'pyyaml',
    ],
    packages=['lojacimport'],
    entry_points={
        'console_scripts': [
            'lojacimport=lojacimport:main'
        ]
    },
)
