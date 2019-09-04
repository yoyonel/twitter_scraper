import pkg_resources


def get_package_version(dist='twitter_analyzer') -> str:
    """

    :param dist:
    """
    return pkg_resources.get_distribution(dist).version
