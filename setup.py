from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dex-aggregator",
    version="0.5.0",
    author="hedeqiang",
    author_email="laravel_code@163.com",
    description="A Python client for interacting with DEX aggregators",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hedeqiang/python_dex_aggregator",
    packages=find_packages(),
    package_data={
        "dex_aggregator": ["core/abis/*.json"],
    },
    install_requires=[
        "eth-typing>=5.1.0",
        "python-dotenv>=1.0.1",
        "requests>=2.32.3",
        "web3>=7.8.0",
        "solders>=0.19.0",
        "solana>=0.30.2",
        "base58>=2.1.1",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
) 