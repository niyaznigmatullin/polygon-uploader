import setuptools
import polygon_uploader

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="polygon-uploader",
    version=polygon_uploader.__version__,
    description="uploader to polygon.codeforces.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/niyaznigmatullin/polygon-uploader",
    author="Niyaz Nigmatullin",
    install_requires=[
        'polygon-api>=1.0a7',
        'requests',
        'pyyaml',
        'progressbar2',
        'beautifulsoup4',
    ],
    packages=['polygon_uploader',
              'polygon_uploader.common',
              'polygon_uploader.lojac',
              'polygon_uploader.usaco',
    ],
    entry_points={
        'console_scripts': [
            'lojacimport=polygon_uploader.lojac:main',
            'usacoimport=polygon_uploader.usaco:main',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
