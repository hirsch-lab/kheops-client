#!/usr/bin/env python
import sys
import logging
import argparse
from pathlib import Path


def import_client():
    # Import kheops_client. If we are in a development environment,
    # import the package from there.
    project_dir = Path(__file__).absolute().parent.parent
    package_dir = project_dir / "kheops_client"
    if (package_dir.is_dir()):
        sys.path.insert(0, str(project_dir))
    import kheops_client
    if Path(kheops_client.__file__).parent == package_dir:
        msg = "Using development version of kheops_client!"
        print("="*len(msg))
        print(msg)
        print("="*len(msg))
        print()
    return kheops_client.KheopsClient


def setup_logging(verbosity):
    logging.addLevelName(logging.DEBUG,   "DEBUG")
    logging.addLevelName(logging.INFO,    "INFO")
    logging.addLevelName(logging.WARNING, "WARN")
    logging.addLevelName(logging.ERROR,   "ERROR")
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity == 2:
        level = logging.DEBUG
    fmt = "%(levelname)-5s: [%(name)-10s] %(message)s"
    fmt = "%(levelname)-5s: %(message)s"
    logging.basicConfig(level=logging.WARNING, format=fmt)
    logger = logging.getLogger("cli")
    logger.setLevel(level)
    return logger


def run_client(args):
    logger = setup_logging(args.verbosity)
    KheopsClient = import_client()
    token = args.token
    client = KheopsClient(url=args.url,
                          access_token=args.token,
                          show_progress=True,
                          dry_run=args.dry,
                          verbosity=args.verbosity)
    # Filter dictionary: DICOM tag -> value
    # Override StudyInstanceUID or SeriesInstanceUID if
    # --study-uid or --series-uid are provided.
    filters = dict(args.search_filter)
    if args.study_uid:
        filters["StudyInstanceUID"] = args.study_uid
    if args.series_uid:
        filters["SeriesInstanceUID"] = args.series_uid
    if args.mode == "series":
        if args.command=="list":
            logger.debug("Action - list series")
            ret = client.list_series(search_filters=filters,
                                     fuzzy=args.fuzzy,
                                     offset=args.offset,
                                     limit=args.limit,
                                     out_dir=args.out_dir)
        elif args.command=="download" and args.study_uid and args.series_uid:
            logger.debug("Action: download single series")
            client.download_series(study_uid=args.study_uid,
                                   series_uid=args.series_uid,
                                   meta_only=args.meta_only,
                                   out_dir=args.out_dir,
                                   forced=args.forced)
        elif args.command=="download":
            logger.debug("Action: download multiple series")
            client.search_and_download_series(search_filters=filters,
                                              meta_only=args.meta_only,
                                              out_dir=args.out_dir,
                                              limit=args.limit,
                                              offset=args.offset,
                                              fuzzy=args.fuzzy,
                                              forced=args.forced)
        else:
            assert False
    elif args.mode == "studies":
        if args.command=="list":
            logger.debug("Action - list studies")
            ret = client.list_studies(search_filters=filters,
                                      fuzzy=args.fuzzy,
                                      offset=args.offset,
                                      limit=args.limit,
                                      out_dir=args.out_dir)
        elif args.command=="download" and args.study_uid:
            logger.debug("Action: download single study")
            client.download_study(study_uid=args.study_uid,
                                  meta_only=args.meta_only,
                                  out_dir=args.out_dir,
                                  forced=args.forced)
        elif args.command=="download":
            logger.debug("Action: download multiple studies")
            client.search_and_download_studies(search_filters=filters,
                                               meta_only=args.meta_only,
                                               out_dir=args.out_dir,
                                               limit=args.limit,
                                               offset=args.offset,
                                               fuzzy=args.fuzzy,
                                               forced=args.forced)
        else:
            assert False
    else:
        assert False, "This mode does not exist: %s" % args.mode


def _add_args(parser):
    info = ("Use option --url to specify the address of the Kheops DICOM\n"
            "repository. It is further required to set an access token,\n"
            "which can be passed either by means of command line argument\n"
            "--token or environment variable ACCESS_TOKEN.\n\n"
            "More about tokens: https://docs.kheops.online/docs/tokens")
    parser_group1 = parser.add_argument_group("General options",
                                              description=info)
    parser_group1.add_argument("-u", "--url", type=str, required=True,
                               help="URL to DICOM repository (WebDICOM API)")
    # About tokens: https://docs.kheops.online/docs/tokens
    info = ("Token to access the repository\n"
            "If not provided, the environment\n"
            "variable ACCESS_TOKEN is used if set.")
    parser_group1.add_argument("-t", "--token", default=None, type=str,
                               help=info)
    _add_general_opts(parser_group1, create_group=False)

    parser_group2 = parser.add_argument_group("Search options")
    parser_group2.add_argument("-x", "--study-uid", default=None,
                               help="Study instance UID")
    parser_group2.add_argument("-y", "--series-uid", default=None,
                               help="Series instance UID")
    info = ("Filter to identify subsets of studies/series\n"
            "It is possible to use the option multiple times\n"
            "For example:\n"
            "   --search-filter PatientID ABC123\n"
            "   --search-filter Modality CT\n"
            "   --search-filter StudyInstanceUID 123.456\n")
    parser_group2.add_argument("--search-filter", nargs=2, action="append",
                               metavar=("KEY","VALUE"), default=[], help=info)
    parser_group2.add_argument("--fuzzy", action="store_true",
                               help="Use fuzzy semantic matching")
    parser_group2.add_argument("--limit", default=None, type=int,
                               help="Limit maximum number of results")
    parser_group2.add_argument("--offset", default=None, type=int,
                               help="Number of results that should be skipped")

    parser_group3 = parser.add_argument_group("I/O options")
    parser_group3.add_argument("-o", "--out-dir", default="./downloads",
                               help="Output directory")
    parser_group3.add_argument("-f", "--forced", action="store_true",
                               help="Overwrite existing files or folders")
    parser_group3.add_argument("-m", "--meta-only", action="store_true",
                               help="Query only the DICOM meta data")
    parser_group3.add_argument("-d", "--dry", action="store_true",
                               help="Dry run, no write actions")

    parser.set_defaults(func=run_client)


def _add_general_opts(parser, create_group=True):
    if create_group:
        parser_opts = parser.add_argument_group("General options")
    else:
        parser_opts = parser
    parser_opts.add_argument("-v", "--verbosity", action="count",
                             help="Increase verbosity")
    parser_opts.add_argument("-h", "--help", action="help",
                             help="Show this help text")


def _add_subsubparsers(parser, command, formatter):
    subparsers = parser.add_subparsers(dest="mode",
                                       title="Modes",
                                       description=None)
    subparsers.required = True

    command = command.capitalize()
    info = "{} single or multiple {} from the Kheops DICOM repository"
    info = info.format(command, "series")
    parser_list = subparsers.add_parser("series",
                                        add_help=False,
                                        description=info,
                                        formatter_class=formatter)
    _add_args(parser_list)

    info = "{} single or multiple {} from the Kheops DICOM repository"
    info = info.format(command, "studies")
    parser_down = subparsers.add_parser("studies",
                                        add_help=False,
                                        description=info,
                                        formatter_class=formatter)
    _add_args(parser_down)

def _parse_args():
    # kheops_client list series
    # kheops_client list studies
    # kheops_client download series
    # kheops_client download studies
    formatter = argparse.RawTextHelpFormatter
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(add_help=False,
                                     formatter_class=formatter)
    _add_general_opts(parser)

    info = "Available commands for the Kheops client"
    subparsers = parser.add_subparsers(dest="command",
                                       title="Commands",
                                       description=info)
    subparsers.required = True

    info = "List available series or studies in the Kheops DICOM repository"
    parser_list = subparsers.add_parser("list",
                                        add_help=False,
                                        description=info,
                                        formatter_class=formatter)
    _add_subsubparsers(parser=parser_list,
                       command="list",
                       formatter=formatter)
    _add_general_opts(parser_list)

    info = "Download series or studies in the Kheops DICOM repository"
    parser_down = subparsers.add_parser("download",
                                        add_help=False,
                                        description=info,
                                        formatter_class=formatter,)
    _add_subsubparsers(parser=parser_down,
                       command="list",
                       formatter=formatter)
    _add_general_opts(parser_down)
    return parser.parse_args()

def main():
    args = _parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
