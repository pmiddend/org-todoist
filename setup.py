from setuptools import setup

setup(
   name='org-todoist',
   version='1.0',
   description='Convert from todoist to emacs org-mode',
   author='Philipp Middendorf',
   author_email='pmidden@mailbox.org',
   packages=['orgtodoist'],
   install_requires=['todoist-python'],
   entry_points={
    'console_scripts': [
        'org-todoist = orgtodoist:main',
    ],
   },
)
