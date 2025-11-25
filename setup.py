from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fastrep",
    version="2.0.8",
    author="Md. Sazzad Hissain Khan",
    author_email="hissain.khan@gmail.com",
    description="A CLI and web-based tool for tracking daily work activities and generating reports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hissain/fastrep",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "flask>=2.0.0",
        "python-dateutil>=2.8.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "fastrep=fastrep.cli:cli",
            "fastrep-ui=fastrep.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "fastrep": [
            "ui/templates/*.html",
            "ui/static/*.css",
        ],
    },
)
