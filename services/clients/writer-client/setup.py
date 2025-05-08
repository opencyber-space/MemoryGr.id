from setuptools import setup, find_packages

def parse_requirements(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="framedb_writer_client",
    version="0.1.0",
    description="Client library for writing to FrameDB memory, persistent, and stream backends using gRPC and direct APIs.",
    author="Your Name",
    author_email="you@example.com",
    packages=find_packages(exclude=["tests*", "examples*"]),
    install_requires=parse_requirements("requirements.txt"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
