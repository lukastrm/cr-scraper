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
import os.path
from typing import Tuple, Optional, List

import utils
from court import CourtListFetcher
from documents import DocumentsTreeFetcher, ShareholderLists, DocumentsTreeElement
from entity import LegalEntityInformationFetcher
from file import SearchInputDataFileReader, LegalEntityInformationFileWriter, \
    LegalEntityBalanceDatesFileWriter, ShareHolderListsFileWriter
from search import SearchRequestHelper, SearchResultEntry, RECORD_CONTENT_DOCUMENTS, \
    RECORD_CONTENT_LEGAL_ENTITY_INFORMATION, SearchParameters
from service import Session

_OPTION_HELP = "help"
_OPTION_ROWS = "rows"
_OPTION_DELAY = "delay"
_OPTION_REQUEST_LIMIT = "request-limit"
_OPTION_LIMIT_INTERVAL = "limit-interval"
_OPTION_SEARCH_POLICY = "search-policy"
_OPTION_SOURCE_DELIMITER = "source-delimiter"
_OPTION_TARGET_PATH = "target"
_OPTION_TARGET_DELIMITER = "target-delimiter"

SEARCH_POLICY_STRICT = 1
SEARCH_POLICY_NAME = 2
SEARCH_POLICY_KEYWORDS = 3

_OPTION_SEARCH_POLICY_VALUES = {
    "strict": SEARCH_POLICY_STRICT,
    "name": SEARCH_POLICY_NAME,
    "keywords": SEARCH_POLICY_KEYWORDS
}


class RuntimeOptions:
    """This class represents a data structure for runtime options provided by command line arguments."""

    def __init__(self):
        self.help: bool = False
        self.rows: Tuple[int, int] = (0, 0)
        self.delay: int = 10
        self.request_limit = 60
        self.limit_interval: int = 60 * 60
        self.search_policy: int = SEARCH_POLICY_STRICT
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
            match = re.match(r"^(\d*),(\d*)$", raw_value)

            if match:
                raw_lower = match.group(1)
                raw_upper = match.group(2)

                lower = int(raw_lower) if raw_lower else 0
                upper = int(raw_upper) if raw_upper else 0

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
        elif option == _OPTION_SEARCH_POLICY:
            if raw_value in _OPTION_SEARCH_POLICY_VALUES.keys():
                self.search_policy = _OPTION_SEARCH_POLICY_VALUES[raw_value]
            else:
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
        file = args[1]

        if not os.path.exists(file):
            print("File does not exist or is not accessible: {}".format(file))
            return
    else:
        print("No file provided")
        sys.exit(1)

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
                options.set_option(option, arg.lower())
                option = None

    if option is not None:
        options.set_option(option, None)

    if options.help:
        print("Usage: PROG [file] [[Option] [Value]]")
        return

    # Initialize logger
    utils.init_logger()
    logger = utils.LOGGER

    # Log session options
    if options.rows[0] > 0 or options.rows[1] > 0:
        lower = options.rows[0]
        upper = options.rows[1]
        logger.info("Restricting analysis to input rows {} to {}"
                    .format(lower if lower > 0 else "(first)", upper if upper > 0 else "(last)"))

    if options.delay > 0:
        logger.info("Request delay: {} seconds".format(options.delay))
    else:
        logger.info("No request delay set")

    if options.request_limit > 0 and options.limit_interval > 0:
        logger.info("Request limit: {} per {} seconds".format(options.request_limit, options.limit_interval))
    else:
        logger.info("No request limit set")

    if options.search_policy == SEARCH_POLICY_STRICT:
        logger.info("Using (default) strict search policy")
    elif options.search_policy == SEARCH_POLICY_NAME:
        logger.info("Using less strict name search policy")
    elif options.search_policy == SEARCH_POLICY_KEYWORDS:
        logger.info("Using vague keywords search policy")
    else:
        logger.warning("Unknown search policy, using default strict search policy")
        options.search_policy = SEARCH_POLICY_STRICT

    if options.source_delimiter:
        logger.info("Using source delimiter: {}".format(options.source_delimiter))

    if options.target_delimiter:
        logger.info("Using source delimiter: {}".format(options.target_delimiter))

    # Set the target directory path for output files
    path = ""

    if options.target_path:
        if not os.path.isdir(options.target_path):
            print("Target path must be a directory: {}".format(options.target_path))
            sys.exit(1)

        path += options.target_path + os.path.sep

    # Initialize web service session
    logger.info("Starting session")
    session = Session(delay=options.delay, request_limit=options.request_limit, limit_interval=options.limit_interval)
    session.initialize()

    if not session.identifier:
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
                if i < options.rows[0] - 1:
                    continue
                elif 0 < options.rows[1] <= i:
                    break

            if record is None:
                continue

            if session.is_limit_reached():
                if search_request_counter > 0:
                    logger.info("Reached request limit after search record {}, delaying request"
                                .format(search_request_counter))

                print("> Delaying request{}\r".format(" " * 40))

            session.make_limited_request()

            # Set search parameters according to search input request
            search_parameters = SearchParameters(keywords=record.name, register_type=record.registry_type,
                                                 register_id=record.registry_id, search_option_deleted=True,
                                                 keywords_option=SearchParameters.KEYWORDS_OPTION_EQUAL_NAME)

            search_policy = options.search_policy

            # Resolve registry court identifier from name
            if record.registry_court is not None:
                court = court_list.get_from_name(record.registry_court)

                if court is None:
                    court = court_list.get_closest_from_name(record.registry_court)

                    if court is None:
                        logger.warning("No court identifier found for {}".format(record.registry_court))
                    else:
                        logger.warning("Closest match for {} is court {} with identifier {}"
                                       .format(record.simple_string(), court.name, court.identifier))

                search_parameters.registry_court = court.identifier

            search_request_counter = i + 1
            print("> Processing record {}{}\r".format(search_request_counter, " " * 40), end="")

            search_result: Optional[List[SearchResultEntry]] = None

            # Perform search request for strict search policy
            if search_policy == SEARCH_POLICY_STRICT:
                search_result = search_request_helper.perform_request(search_parameters)

                if search_result is not None and len(search_result) == 0:
                    search_policy = SEARCH_POLICY_NAME

                    # Repeat search request in case of missing results without formal registry information
                    logger.info("No exact result for {}, retrying with name search policy"
                                .format(record.name, record.registry_type, record.registry_id, record.registry_court))

            # Perform search request for search policy with matching name
            if search_policy == SEARCH_POLICY_NAME:
                search_parameters.registry_type = None
                search_parameters.registry_id = None
                search_parameters.registry_court = None

                search_result = search_request_helper.perform_request(search_parameters)

                if search_result is not None and len(search_result) == 0:
                    search_policy = SEARCH_POLICY_KEYWORDS

                    # Repeat search request in case of missing results with less strict keywords matching
                    logger.info("No exact result for {}, retrying with name keywords policy"
                                .format(record.name, record.registry_type, record.registry_id, record.registry_court))

            # Perform search request for search policy with just keywords
            if search_policy == SEARCH_POLICY_KEYWORDS:
                search_parameters.registry_type = None
                search_parameters.registry_id = None
                search_parameters.registry_court = None
                search_parameters.keywords_option = SearchParameters.KEYWORDS_OPTION_ALL
                search_result = search_request_helper.perform_request(search_parameters)

                if search_result is not None and len(search_result) == 0:
                    logger.error("No result for {}".format(record.simple_string()))
                    continue
                else:
                    logger.warning("The search result for {} might not be identical to the desired legal entity"
                                   .format(record.simple_string()))

            if search_result is None:
                logger.error("Could not perform search request for {}".format(record.simple_string()))
                continue
            elif len(search_result) > 1:
                logger.error("Too many results for {}".format(record.simple_string()))
                continue

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

            search_request_successful += 1

            entity_information_writer.write(entity_information, search_policy)
            balance_dates_writer.write(entity_information)

            if result.record_has_content(RECORD_CONTENT_DOCUMENTS):
                # Fetch shareholder lists if documents exist for that record
                documents_tree_fetcher = DocumentsTreeFetcher(session)
                documents: Optional[DocumentsTreeElement] = documents_tree_fetcher.fetch(result)

                if documents is None:
                    logger.warning("Cannot fetch shareholder lists for {}".format(entity_information.name))
                else:
                    shareholder_lists_writer.write(ShareholderLists(entity_information, documents))

    logger.info("{} out of {} search requests were successful ({:.2f} % success rate)".
                format(search_request_successful, search_request_counter,
                       search_request_successful * 100 / max(search_request_counter, 1)))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Terminating")
        pass
