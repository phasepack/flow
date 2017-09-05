from setuptools import setup

install_requires = ["numpy", "scipy"]

setup(name="flow",
      version="0.1",
      description="A framework for constructing numerical algorithms from linearly or iteratively chainable flows",
      url="https://github.com/phasepack/flow",
      author="Noah Singer",
      author_email="",
      license="GNU GPLv3",
      packages=["flow"],
      zip_safe=False)
