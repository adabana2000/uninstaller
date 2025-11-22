from setuptools import setup, find_packages

setup(
    name="windows-uninstaller",
    version="0.8.0",
    description="Advanced Windows application uninstaller with leftover cleanup and quick actions",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.6.0",
        "click>=8.1.0",
        "pywin32>=306",
        "python-dateutil>=2.8.0",
        "tabulate>=0.9.0",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "uninstaller=cli.commands:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
