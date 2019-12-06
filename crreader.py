"""
Copyright (c) 2019 trm factory, Lukas Trommer
All rights reserved.

These software resources were developed for the Entrepreneurial Group Dynamics research project at the
Technical University of Berlin.
Every distribution, modification, performing and every other type of usage is strictly prohibited if not
explicitly allowed by the package license agreement, service contract or other legal regulations.
"""
import sys
import os.path

from comreg.file import SearchInputDataFileReader, LegalEntityInformationFileWriter, LegalEntityBalanceDatesFileWriter
from comreg.search import CRSearch, PARAM_REGISTER_TYPE, PARAM_REGISTER_COURT, PARAM_REGISTER_ID, PARAM_KEYWORDS, \
    CRSearchResultEntry, CRLegalEntityInformationLookUp
from comreg.session import CRSession


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

    session = CRSession()
    session.run()

    if not session:
        return

    with SearchInputDataFileReader(files[0]) as reader, \
            LegalEntityInformationFileWriter("information.csv") as information_writer, \
            LegalEntityBalanceDatesFileWriter("balances.csv") as balance_writer:
        for record in reader:
            search = CRSearch(session)
            search.set_param(PARAM_REGISTER_TYPE, record.registry_type)
            search.set_param(PARAM_REGISTER_ID, record.registry_id)
            search.params[PARAM_KEYWORDS] = record.name
            # search.params[PARAM_REGISTER_COURT] = record.registry_court
            search.run()

            print("{} {} at {}: {}".format(record.registry_type, record.registry_id, record.registry_court, search.result))

            if len(search.result) == 0:
                print("No result")
                continue
            elif len(search.result) == 1:
                result = search.result[0]
            else:
                print("Too many results")
                continue

            information = CRLegalEntityInformationLookUp(session, result.index)
            information.fetch()

            if information.result is not None:
                information_writer.write(information.result)
                balance_writer.write(information.result)


if __name__ == "__main__":
    main()
