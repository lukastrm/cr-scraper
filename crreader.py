"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import re
import sys
import logging
import os.path
from typing import Tuple, Optional

from comreg.court import CourtListFetcher
from comreg.entity import LegalEntityInformationFetcher
from comreg.file import SearchInputDataFileReader, LegalEntityInformationFileWriter, LegalEntityBalanceDatesFileWriter
from comreg.search import SearchRequest, PARAM_REGISTER_TYPE, PARAM_REGISTER_COURT, PARAM_REGISTER_ID, PARAM_KEYWORDS, \
    PARAM_KEYWORD_OPTIONS, KEYWORD_OPTION_ALL, PARAM_SEARCH_OPTION_DELETED, KEYWORD_OPTION_EQUAL_NAME
from comreg.service import Session

SYS_ARG_NAME_DELAY = "delay"
SYS_ARG_NAME_COOLDOWN = "cooldown"


_OPTION_HELP = "help"
_OPTION_LINES = "lines"
_OPTION_DELAY = "delay"
_OPTION_REQUEST_LIMIT = "request-limit"
_OPTION_LIMIT_INTERVAL = "limit-interval"


class RuntimeOptions:

    def __init__(self):
        self.help: bool = False
        self.rows: Tuple[int, int] = None
        self.delay: int = 10
        self.request_limit = 60
        self.limit_interval: int = 60 * 60

    def set_option(self, option: str, raw_value: Optional[str]) -> None:
        invalid = False

        if not option:
            print("Ignoring empty option")
            return

        if option == _OPTION_HELP:
            self.help = True
        elif option == _OPTION_LINES:
            match = re.match(r"^(\d*),(\d*)$", raw_value)
            raw_lower = match.group(1)
            raw_upper = match.group(2)

            lower = int(raw_lower) if raw_lower else -1
            upper = int(raw_upper) if raw_upper else -1

            if match:
                if lower >= 0 and 0 <= upper < lower:
                    lower = upper

                self.rows = (lower, upper)
            else:
                invalid = True
        elif option == _OPTION_DELAY:
            if re.match(r"\d+", raw_value):
                delay = int(raw_value)

                if delay > 0:
                    self.delay = delay
                    return

            invalid = True
        elif option == _OPTION_REQUEST_LIMIT:
            if re.match(r"\d+", raw_value):
                limit = int(raw_value)

                if limit > 0:
                    self.request_limit = int(raw_value)
                    return

            invalid = True
        elif option == _OPTION_LIMIT_INTERVAL:
            if re.match(r"\d+", raw_value):
                interval = int(raw_value)

                if interval > 0:
                    self.limit_interval = interval
                    return

            invalid = True
        else:
            print("Ignoring value for unknown option {}".format(option))

        if invalid:
            print("Invalid value {} for option --{}".format(raw_value, option))


def main():
    args = sys.argv
    arg_len = len(args)

    if arg_len == 0:
        raise ValueError
    if arg_len == 1:
        print("Usage: crreader <File>([, <File>]) ([<Option> <Value>])")
        return

    files = []
    read_options = False
    options = RuntimeOptions()
    option = None

    for arg in args[1:]:
        if arg.startswith("--"):
            arg = arg[2:]

            if not read_options:
                read_options = True

            if option is not None:
                options.set_option(option, None)
                option = arg
            else:
                option = arg

            continue

        if read_options:
            if option is None:
                print("No option for value {}".format(arg))
            else:
                options.set_option(option, arg)
                option = None
        else:
            if os.path.exists(arg):
                files.append(arg)
            else:
                print("File does not exist or is not accessible: {}".format(arg))
                return

    if option is not None:
        options.set_option(option, None)

    if options.help:
        print("Usage: crreader <File>([, <File>]) ([<Option> <Value>])")
        return

    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("default")

    file_handler = logging.FileHandler("protocol.log")
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    error_file_handler = logging.FileHandler("error.log")
    error_file_handler.setFormatter(log_formatter)
    error_file_handler.setLevel(logging.WARNING)
    logger.addHandler(error_file_handler)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    # Log session options
    if options.rows is not None:
        lower = options.rows[0]
        upper = options.rows[1]
        logger.info("Restricting analysis to input rows {} to {}".format(lower if lower >= 0 else "LOWEST", upper if upper >= 0 else "HIGHEST"))

    if options.delay > 0:
        logger.info("Request delay: {} seconds".format(options.delay))
    else:
        logger.info("No request delay set")

    if options.request_limit > 0 and options.limit_interval > 0:
        logger.info("Request limit: {} per {} seconds".format(options.request_limit, options.limit_interval))
    else:
        logger.info("No request limit set")

    logger.info("Starting session")
    session = Session(delay=options.delay, request_limit=options.request_limit, limit_interval=options.limit_interval)
    session.initialize()

    if not session:
        logger.error("Failed to initialize session")
        return

    logger.info("Initialized session " + session.identifier)

    logger.info("Fetching court list")
    court_list_fetcher = CourtListFetcher(session)
    court_list = court_list_fetcher.run()

    if not court_list:
        logger.error("Failed to fetch court list")

    logger.info("Fetched information for {} registry courts".format(len(court_list)))

    max_search_requests = 100
    search_request_counter: int = 0
    search_request_successful: int = 0

    with SearchInputDataFileReader(files[0]) as reader, \
            LegalEntityInformationFileWriter("information.csv") as information_writer, \
            LegalEntityBalanceDatesFileWriter("balances.csv") as balance_writer:
        for record in reader:
            if session.is_limit_reached():
                logger.info("Reached request limit, delaying request")

            session.make_limited_request()

            search = SearchRequest(session)
            search.set_param(PARAM_KEYWORDS, record.name)
            search.set_param(PARAM_REGISTER_TYPE, record.registry_type)
            search.set_param(PARAM_REGISTER_ID, record.registry_id)
            search.set_param(PARAM_KEYWORD_OPTIONS, KEYWORD_OPTION_EQUAL_NAME)
            search.set_param(PARAM_SEARCH_OPTION_DELETED, True)

            if record.registry_court is not None:
                court = court_list.get_from_name(record.registry_court)

                if court is None:
                    court = court_list.get_closest_from_name(record.registry_court)

                    if court is None:
                        logger.warning("No court identifier found for {}".format(record.registry_court))
                    else:
                        logger.warning("Closest match for {} is court {} with identifier {}"
                                       .format(record.registry_court, court.name, court.identifier))

                search.set_param(PARAM_REGISTER_COURT, court.identifier)

            search.run()
            search_request_counter += 1

            if len(search.result) == 0:
                logger.info("No exact result for name {} with identifier {} {} at court {}, retrying with different "
                            "search options".
                            format(record.name, record.registry_type, record.registry_id, record.registry_court))

                search.set_param(PARAM_REGISTER_TYPE, "")
                search.set_param(PARAM_REGISTER_ID, "")
                search.set_param(PARAM_REGISTER_COURT, "")
                search.run()

                if len(search.result) == 0:
                    search.set_param(PARAM_KEYWORD_OPTIONS, KEYWORD_OPTION_ALL)
                    search.run()

                    if len(search.result) == 0:
                        logger.warning("No result for name {} with identifier {} {} at court {}".
                                       format(record.name, record.registry_type, record.registry_id,
                                              record.registry_court))
                        continue
                    else:
                        logger.warning("The search result for {} might no be identical to the desired legal entity"
                                       .format(record.name))

            if len(search.result) > 1:
                logger.warning("Too many results for name {} with identifier {} {} at court {}".
                               format(record.name, record.registry_type, record.registry_id, record.registry_court))
                continue

            search_request_successful += 1
            result = search.result[0]

            information = LegalEntityInformationFetcher(session, result)
            information.fetch()

            if information.result is not None:
                logger.info("Found entity information for {}".format(information.result.name))
                information_writer.write(information.result)
                balance_writer.write(information.result)

            if max_search_requests <= search_request_counter:
                break

    logger.info("{} out of {} search requests were successful ({:.2f} % success rate)".
                format(search_request_successful, search_request_counter,
                       search_request_successful * 100 / search_request_counter))


if __name__ == "__main__":
    main()
