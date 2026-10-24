"""Offline Knowledge content downloader.

Keeps <data_path>/zim in line with the selected profile, languages and extra
sources, using the Kiwix OPDS catalog. Independent of the library server: it
only writes ZIM files into a folder.
"""

__version__ = "0.2.0"

USER_AGENT = (
    f"offline-knowledge-ha-app/{__version__} "
    "(+https://github.com/ToBeHH/homeassistant-apps)"
)
