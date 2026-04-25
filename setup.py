# LogHunter Package Setup
from setuptools import setup, find_packages

setup(
    name="loghunter",
    version="1.0.0",
    description="日志智能检索与诊断Agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "langgraph>=0.2.0",
        "pyyaml>=6.0",
        "requests>=2.32.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-mock>=3.14.0",
            "pytest-cov>=5.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "loghunter=cli.main:main",
        ]
    },
)