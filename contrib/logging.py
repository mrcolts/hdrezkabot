import logging


def create_logger(name, level=None):
    logging.basicConfig(level=level or logging.DEBUG,
                        format='[%(asctime)s] %(filename)s[%(lineno)d] %(name)s %(levelname)s %(message)s',
                        datefmt="%d/%m/%Y %H:%M:%S")
    return logging.getLogger(name)
