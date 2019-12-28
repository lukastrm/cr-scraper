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
from typing import Tuple, Optional, List

from comreg.court import CourtListFetcher
from comreg.documents import ShareholderListsFetcher, ShareholderLists
from comreg.entity import LegalEntityInformationFetcher
from comreg.file import SearchInputDataFileReader, LegalEntityInformationFileWriter, \
    LegalEntityBalanceDatesFileWriter, ShareHolderListsFileWriter
from comreg.search import SearchRequestHelper, SearchResultEntry, RECORD_CONTENT_DOCUMENTS, \
    RECORD_CONTENT_LEGAL_ENTITY_INFORMATION, SearchParameters
from comreg.service import Session

SYS_ARG_NAME_DELAY = "delay"
SYS_ARG_NAME_COOLDOWN = "cooldown"

_OPTION_HELP = "help"
_OPTION_ROWS = "rows"
_OPTION_DELAY = "delay"
_OPTION_REQUEST_LIMIT = "request-limit"
_OPTION_LIMIT_INTERVAL = "limit-interval"
_OPTION_SOURCE_DELIMITER = "source-delimiter"
_OPTION_TARGET_PATH = "target"
_OPTION_TARGET_DELIMITER = "target-delimiter"


class RuntimeOptions:
    """This class represents a data structure for runtime options provided by command line arguments."""

    def __init__(self):
        self.help: bool = False
        self.rows: Tuple[int, int] = None
        self.delay: int = 10
        self.request_limit = 60
        self.limit_interval: int = 60 * 60
        self.source_delimiter = None
        self.target_path = None
        self.target_delimiter = None

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
        elif option == _OPTION_SOURCE_DELIMITER:
            self.source_delimiter = raw_value
        elif option == _OPTION_TARGET_PATH:
            self.target_path = raw_value
        elif option == _OPTION_TARGET_DELIMITER:
            self.target_delimiter = raw_value
        else:
            print("Ignoring value for unknown option {}".format(option))

        if invalid:
            print("Invalid value {} for option --{}".format(raw_value, option))


def main():
    """Main function"""

    # Parse command line arguments and set runtime options accordingly
    args = sys.argv
    file = None
    options = RuntimeOptions()
    option = None

    if len(args) > 1:
        if os.path.exists(args[1]):
            file = args[1]
        else:
            print("File does not exist or is not accessible: {}".format(file))
            return
    else:
        print("No file provided")

    if len(args) > 2:
        for arg in args[2:]:
            if arg.startswith("--"):
                arg = arg[2:]

                if option is not None:
                    options.set_option(option, None)
                    option = arg
                else:
                    option = arg

                continue

            if option is None:
                print("No option for value {}".format(arg))
            else:
                options.set_option(option, arg)
                option = None

    if option is not None:
        options.set_option(option, None)

    if options.help:
        print("Usage: crreader <File> ([<Option> <Value>])")
        return

    # Initialize logger
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
        logger.info("Restricting analysis to input row indices {} to {}"
                    .format(max(lower, 0), upper if upper >= 0 else "MAX"))

    if options.delay > 0:
        logger.info("Request delay: {} seconds".format(options.delay))
    else:
        logger.info("No request delay set")

    if options.request_limit > 0 and options.limit_interval > 0:
        logger.info("Request limit: {} per {} seconds".format(options.request_limit, options.limit_interval))
    else:
        logger.info("No request limit set")

    if options.source_delimiter:
        logger.info("Using source delimiter: {}".format(options.source_delimiter))

    if options.target_delimiter:
        logger.info("Using source delimiter: {}".format(options.target_delimiter))

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

    # Set default CSV delimiters if no other values were provided
    if not options.source_delimiter:
        options.source_delimiter = ","

    if not options.target_delimiter:
        options.target_delimiter = ","

    search_request_helper = SearchRequestHelper(session)

    # Read search input records and initialize writers
    with SearchInputDataFileReader(file, delimiter=options.source_delimiter) as reader, \
            LegalEntityInformationFileWriter(path + "entity-information.csv", delimiter=options.target_delimiter) \
                    as entity_information_writer, \
            LegalEntityBalanceDatesFileWriter(path + "balance-dates.csv", delimiter=options.target_delimiter) \
                    as balance_dates_writer, \
            ShareHolderListsFileWriter(path + "shareholder-lists.csv", delimiter=options.target_delimiter) \
                    as shareholder_lists_writer:

        # Iterate through all search input records
        for i, record in enumerate(reader):
            if options.rows is not None:
                if i < options.rows[0]:
                    continue
                elif 0 <= options.rows[1] <= i:
                    break

            if record is None:
                continue

            if session.is_limit_reached():
                logger.info("Reached request limit, delaying request")

            session.make_limited_request()

            # Set search parameters according to search input request
            search_parameters = SearchParameters(keywords=record.name, register_type=record.registry_type,
                                                 register_id=record.registry_id, search_option_deleted=True,
                                                 keywords_option=SearchParameters.KEYWORDS_OPTION_EQUAL_NAME)

            # Resolve registry court identifier from name
            if record.registry_court is not None:
                court = court_list.get_from_name(record.registry_court)

                if court is None:
                    court = court_list.get_closest_from_name(record.registry_court)

                    if court is None:
                        logger.warning("No court identifier found for {}".format(record.registry_court))
                    else:
                        logger.warning("Closest match for {} is court {} with identifier {}"
                                       .format(record.registry_court, court.name, court.identifier))

                search_parameters.registry_court = court.identifier

            # Perform search request
            search_result: List[SearchResultEntry] = search_request_helper.perform_request(search_parameters)
            search_request_counter += 1

            if len(search_result) == 0:
                # Repeat search request in case of missing results without formal registry information
                logger.info("No exact result for name {} with identifier {} {} at court {}, retrying with different "
                            "search options".
                            format(record.name, record.registry_type, record.registry_id, record.registry_court))

                search_parameters.registry_type = None
                search_parameters.registry_id = None
                search_parameters.registry_court = None

                search_result = search_request_helper.perform_request(search_parameters)

                if len(search_result) == 0:
                    # Repeat search request in case of missing results with less strict keyword matching
                    search_parameters.keywords_option = SearchParameters.KEYWORDS_OPTION_ALL
                    search_result = search_request_helper.perform_request(search_parameters)

                    if len(search_result) == 0:
                        logger.warning("No result for name {} with identifier {} {} at court {}".
                                       format(record.name, record.registry_type, record.registry_id,
                                              record.registry_court))
                        continue
                    else:
                        logger.warning("The search result for {} might no be identical to the desired legal entity"
                                       .format(record.name))

            if len(search_result) > 1:
                logger.warning("Too many results for name {} with identifier {} {} at court {}".
                               format(record.name, record.registry_type, record.registry_id, record.registry_court))
                continue

            search_request_successful += 1
            result: SearchResultEntry = search_result[0]

            # Check if the search result indicates the existence of legal entity information data,
            # which should always be True
            if not result.record_has_content(RECORD_CONTENT_LEGAL_ENTITY_INFORMATION):
                logger.warning("No legal entity information indicator for {}".format(result.name))
                continue

            # Fetch legal entity information
            entity_information_fetcher = LegalEntityInformationFetcher(session, result)
            entity_information = entity_information_fetcher.fetch()

            if entity_information is None:
                logger.warning("Cannot fetch detailed information for {}".format(result.name))
                continue

            entity_information_writer.write(entity_information)
            balance_dates_writer.write(entity_information)

            if result.record_has_content(RECORD_CONTENT_DOCUMENTS):
                # Fetch shareholder lists if documents exist for that record
                lists_fetcher = ShareholderListsFetcher(session)
                shareholder_lists: ShareholderLists = lists_fetcher.fetch(result, entity_information)

                if shareholder_lists is None:
                    logger.warning("Cannot fetch shareholder lists for {}".format(entity_information.name))
                else:
                    shareholder_lists_writer.write(shareholder_lists)

    logger.info("{} out of {} search requests were successful ({:.2f} % success rate)".
                format(search_request_successful, search_request_counter,
                       search_request_successful * 100 / max(search_request_counter, 1)))


if __name__ == "__main__":
    main()
