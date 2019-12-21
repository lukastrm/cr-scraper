"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import sys
import logging
import os.path
from time import sleep

from comreg.court import CourtListFetcher
from comreg.entity import LegalEntityInformationFetcher
from comreg.file import SearchInputDataFileReader, LegalEntityInformationFileWriter, LegalEntityBalanceDatesFileWriter
from comreg.search import SearchRequest, PARAM_REGISTER_TYPE, PARAM_REGISTER_COURT, PARAM_REGISTER_ID, PARAM_KEYWORDS, \
    PARAM_KEYWORD_OPTIONS, KEYWORD_OPTION_ALL, PARAM_SEARCH_OPTION_DELETED, KEYWORD_OPTION_EQUAL_NAME
from comreg.service import Session

SYS_ARG_NAME_DELAY = "delay"
SYS_ARG_NAME_COOLDOWN = "cooldown"


def main():
    args = sys.argv
    arg_len = len(args)

    if arg_len == 0:
        raise ValueError
    if arg_len == 1:
        print("Usage: crreader <File>([, <File>]) ([<Flag> <Argument>])")
        return

    files = []
    flags = False

    for arg in args[1:]:
        if not flags and arg.startswith("--"):
            flags = True

        if flags:
            pass
        else:
            if os.path.exists(arg):
                files.append(arg)
            else:
                print("File does not exist or is not accessible: {}".format(arg))
                return

    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger()

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

    logger.info("Starting session")
    session = Session()
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
                        logger.warning("Closest match for {} is court {} with identifier {}".format(record.registry_court, court.name, court.identifier))

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
            sleep(3)

            information = LegalEntityInformationFetcher(session, result)
            information.fetch()

            if information.result is not None:
                logger.info("Found entity information for {}".format(information.result.name))
                information_writer.write(information.result)
                balance_writer.write(information.result)

            if max_search_requests <= search_request_counter:
                break

            sleep(5)

    logger.info("{} out of {} search requests were successful ({:.2f} % success rate)".
                format(search_request_successful, search_request_counter,
                       search_request_successful * 100 / search_request_counter))


if __name__ == "__main__":
    main()
