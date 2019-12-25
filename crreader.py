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
from comreg.documents import ShareholderListsFetcher, ShareholderLists
from comreg.entity import LegalEntityInformationFetcher
from comreg.file import SearchInputDataFileReader, LegalEntityInformationFileWriter, \
    LegalEntityBalanceDatesFileWriter, ShareHolderListsFileWriter
from comreg.search import SearchRequest, PARAM_REGISTER_TYPE, PARAM_REGISTER_COURT, PARAM_REGISTER_ID, PARAM_KEYWORDS, \
    PARAM_KEYWORD_OPTIONS, KEYWORD_OPTION_ALL, PARAM_SEARCH_OPTION_DELETED, KEYWORD_OPTION_EQUAL_NAME, \
    SearchResultEntry, RECORD_CONTENT_DOCUMENTS, RECORD_CONTENT_LEGAL_ENTITY_INFORMATION
from comreg.service import Session

SYS_ARG_NAME_DELAY = "delay"
SYS_ARG_NAME_COOLDOWN = "cooldown"


_OPTION_HELP = "help"
_OPTION_ROWS = "rows"
_OPTION_DELAY = "delay"
_OPTION_REQUEST_LIMIT = "request-limit"
_OPTION_LIMIT_INTERVAL = "limit-interval"
_OPTION_TARGET_PATH = "target"


class RuntimeOptions:

    def __init__(self):
        self.help: bool = False
        self.rows: Tuple[int, int] = None
        self.delay: int = 10
        self.request_limit = 60
        self.limit_interval: int = 60 * 60
        self.target_path = None

    def set_option(self, option: str, raw_value: Optional[str]) -> None:
        invalid = False

        if not option:
            print("Ignoring empty option")
            return

        if option == _OPTION_HELP:
            self.help = True
        elif option == _OPTION_ROWS:
            match = re.match(r"^(-1|\d*),(-1|\d*)$", raw_value)

            if match:
                raw_lower = match.group(1)
                raw_upper = match.group(2)

                lower = int(raw_lower) if raw_lower else -1
                upper = int(raw_upper) if raw_upper else -1

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
        elif option == _OPTION_TARGET_PATH:
            self.target_path = raw_value
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

    file_handler = logging.FileHandler("protocol.log", "w")
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    error_file_handler = logging.FileHandler("error.log", "w")
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
        logger.info("Restricting analysis to input rows {} to {}".format(lower if lower >= 0 else "LOWEST",
                                                                         upper if upper >= 0 else "HIGHEST"))

    if options.delay > 0:
        logger.info("Request delay: {} seconds".format(options.delay))
    else:
        logger.info("No request delay set")

    if options.request_limit > 0 and options.limit_interval > 0:
        logger.info("Request limit: {} per {} seconds".format(options.request_limit, options.limit_interval))
    else:
        logger.info("No request limit set")

    # Initialize web service session
    logger.info("Starting session")
    session = Session(delay=options.delay, request_limit=options.request_limit, limit_interval=options.limit_interval)
    session.initialize()

    if not session:
        logger.error("Failed to initialize session")
        sys.exit(1)

    logger.info("Initialized session " + session.identifier)

    # Fetch court list to get the correct identifier mapping
    logger.info("Fetching court list")
    court_list_fetcher = CourtListFetcher(session)
    court_list = court_list_fetcher.run()

    if not court_list:
        logger.error("Failed to fetch court list")
        sys.exit(1)

    logger.info("Fetched information for {} registry courts".format(len(court_list)))

    search_request_counter: int = 0
    search_request_successful: int = 0

    # Set the target directory path for output files
    path = ""

    if options.target_path:
        if not os.path.isdir(options.target_path):
            logger.error("Target path must be a directory: {}".format(options.target_path))
            sys.exit(1)

        path += options.target_path + os.path.sep

    with SearchInputDataFileReader(files[0]) as reader, \
            LegalEntityInformationFileWriter(path + "entity-information.csv") as entity_information_writer, \
            LegalEntityBalanceDatesFileWriter(path + "balance-dates.csv") as balance_dates_writer, \
            ShareHolderListsFileWriter(path + "shareholder-lists.csv") as shareholder_lists_writer:
        for i, record in enumerate(reader):
            if options.rows is not None:
                if i < options.rows[0]:
                    continue
                elif 0 <= options.rows[1] <= i:
                    break

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
            result: SearchResultEntry = search.result[0]

            # Check if the search result indicates the existence of legal entity information data,
            # which should always be True
            if not result.record_has_content(RECORD_CONTENT_LEGAL_ENTITY_INFORMATION):
                logger.warning("No legal entity information indicator for {}".format(result.name))
                continue

            entity_information_fetcher = LegalEntityInformationFetcher(session, result)
            entity_information = entity_information_fetcher.fetch()

            if entity_information is None:
                logger.warning("Cannot fetch detailed information for {}".format(result.name))
                continue

            entity_information_writer.write(entity_information)
            balance_dates_writer.write(entity_information)

            if result.record_has_content(RECORD_CONTENT_DOCUMENTS):
                lists_fetcher = ShareholderListsFetcher(session)
                shareholder_lists: ShareholderLists = lists_fetcher.fetch(result, entity_information)

                if shareholder_lists is None:
                    logger.warning("Cannot fetch shareholder lists for {}".format(entity_information.name))

                shareholder_lists_writer.write(shareholder_lists)

    logger.info("{} out of {} search requests were successful ({:.2f} % success rate)".
                format(search_request_successful, search_request_counter,
                       search_request_successful * 100 / search_request_counter))


if __name__ == "__main__":
    main()
