from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in epibus/__init__.py
from epibus import __version__ as version

setup(
	name="epibus",
	version=version,
	description="ERPNext integration with MODBUS/TCP networked programmable logic controllers (PLC)",
	author="Applied Relevance",
	author_email="geveritt@appliedrelevance.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
