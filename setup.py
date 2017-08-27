from setuptools import setup

install_requires = ["numpy", "scipy"]

setup(name="flowarch",
      version="0.1",
      description="A framework for constructing numerical algorithms from linearly or iteratively chainable flows",
      url="https://github.com/phasepack/flowarch",
      author="Noah Singer",
      author_email="",
      license="GNU GPLv3",
      packages=["flowarch"],
      zip_safe=False)
