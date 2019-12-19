"""
Copyright (c) 2020 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import sys
import os.path

from comreg.court import CourtListFetcher
from comreg.entity import LegalEntityInformationFetcher
from comreg.file import SearchInputDataFileReader, LegalEntityInformationFileWriter, LegalEntityBalanceDatesFileWriter
from comreg.search import SearchRequest, PARAM_REGISTER_TYPE, PARAM_REGISTER_COURT, PARAM_REGISTER_ID, PARAM_KEYWORDS
from comreg.service import Session


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

    session = Session()
    session.run()

    if not session:
        return

    court_list_fetcher = CourtListFetcher(session)
    court_list_fetcher.run()
    court_list = court_list_fetcher.result

    max_search_requests = 100
    search_request_counter: int = 0
    search_request_successful: int = 0

    with SearchInputDataFileReader(files[0]) as reader, \
            LegalEntityInformationFileWriter("information.csv") as information_writer, \
            LegalEntityBalanceDatesFileWriter("balances.csv") as balance_writer:
        for record in reader:
            search = SearchRequest(session)
            search.set_param(PARAM_REGISTER_TYPE, record.registry_type)
            search.set_param(PARAM_REGISTER_ID, record.registry_id)
            search.__params[PARAM_KEYWORDS] = record.name

            if record.registry_court is not None:
                court = court_list.get_from_name(record.registry_court)

                if court is None:
                    court, ratio = court_list.get_closest_from_name(record.registry_court)

                    if court is None:
                        print("No court identifier found for {}".format(record.registry_court))
                    else:
                        print("Closest match for {} is court {} with identifier {}".format(record.registry_court, court.name, court.identifier))

            search.__params[PARAM_REGISTER_COURT] = court.identifier
            search.run()
            search_request_counter += 1

            if len(search.result) == 0:
                print("No result for name {} with identifier {} {} at court {}"
                      .format(record.name, record.registry_type, record.registry_id, record.registry_court))
                continue
            elif len(search.result) == 1:
                search_request_successful += 1
                result = search.result[0]
            else:
                print("Too many results for name {} with identifier {} {} at court {}"
                      .format(record.name, record.registry_type, record.registry_id, record.registry_court))
                continue

            information = LegalEntityInformationFetcher(session, result.index)
            information.fetch()

            if information.result is not None:
                print("Found entity information for {}".format(information.result.name))
                information_writer.write(information.result)
                balance_writer.write(information.result)

            if max_search_requests <= search_request_counter:
                break

    print("{} out of {} search requests were successful ({:.2f} % success rate)"
          .format(search_request_successful, search_request_counter,
                  search_request_successful * 100 / search_request_counter))


if __name__ == "__main__":
    main()
