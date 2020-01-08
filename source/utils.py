"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import logging
import sys

LOGGER = None


def init_logger():
    global LOGGER
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    LOGGER = logging.getLogger("default")

    file_handler = logging.FileHandler("protocol.log", "w")
    file_handler.setFormatter(log_formatter)
    LOGGER.addHandler(file_handler)

    error_file_handler = logging.FileHandler("error.log", "w")
    error_file_handler.setFormatter(log_formatter)
    error_file_handler.setLevel(logging.WARNING)
    LOGGER.addHandler(error_file_handler)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(log_formatter)
    LOGGER.addHandler(console_handler)
    LOGGER.setLevel(logging.INFO)
