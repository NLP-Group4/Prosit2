"""
Setup configuration for backend package.
This allows the backend to be installed in development mode.
"""

from setuptools import setup, find_packages

setup(
    name="backend",
    version="2.0.0",
    packages=find_packages(),
    python_requires=">=3.9",
)
