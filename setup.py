from setuptools import setup, find_packages

version = __import__("video_finder").__version__

setup(
        name="simple-youtube-video-finder",
        description="get public video data from youtube.",
        author="Christof Franke",
        author_email="christof@myway.de",
        license="GNU General Public License v3.0",
        platforms=["OS Independent"],
        packages=find_packages(exclude=["tests"]),
        include_package_data=True,
        install_requires=[
            "requests",
        ],
        zip_seafe=False,
)

