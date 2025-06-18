import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.md')) as f:
    CHANGES = f.read()

requires = [
    'jax',
    'matplotlib',
    'ruamel.yaml<0.18.0',
    'pandas',
    'attrs',
    'transaction',
    'sortedcontainers',
    'peakutils',
    'plyvel-win32; platform_system == \'Windows\'',
    'plyvel; platform_system != \'Windows\'',
    ]

setup(name='fatoolsng',
      version='0.1',
      description='fatoolsng',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Programming Language :: Python", ],
      author='Alexandr Dorif',
      author_email='dorif11@gmail.com',
      url='',
      keywords='dna fragment-analysis',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="fatoolsng",
      entry_points="""\
      [console_scripts]
      fatoolsng = fatoolsng.scripts.run:main
      """, )
