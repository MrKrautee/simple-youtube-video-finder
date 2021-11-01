from setuptools import setup

# from requirements-dev.txt
dev = ['pytest', 'flake8']

setup(
    tests_require=['pytest'],
    install_requires=[
        # from requirements.txt
        'requests'],
    extra_requires={'dev': dev},
)