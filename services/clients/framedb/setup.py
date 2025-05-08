from setuptools import setup, find_packages

# Load requirements from requirements.txt
with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

setup(
    name="framedb_sdk",
    version="0.1.0",
    description="Python SDK for interacting with FrameDB (in-memory, persistent, and stream storage)",
    author="Prasanna HN",
    author_email="prasanna@opencyberspace.org",
    url="",  
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
    ],
)
