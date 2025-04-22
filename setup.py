from setuptools import setup, find_packages

setup(
    name="payment-binder",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    author="PrashantChiplunkar",
    author_email="prashantschiplunkar@gmail.com",
    description="Python library to provide payment gateway with different payment providers",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/PrashantChiplunkar/payment-binder",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
