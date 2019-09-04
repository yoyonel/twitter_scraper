from logging import getLogger
from pprint import pformat

from langdetect.detector_factory import DetectorFactory, PROFILES_DIRECTORY

logger = getLogger(__name__)

factory = DetectorFactory()
factory.load_profile(PROFILES_DIRECTORY)
lang_list = factory.get_lang_list() + ['und', ]
logger.debug("lang_list=\n{}".format(pformat(lang_list)))
