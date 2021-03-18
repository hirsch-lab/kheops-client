import os
import time
import logging
import datetime
import pandas as pd
import pydicom as dicom
from pathlib import Path
from collections import defaultdict
from dicomweb_client.api import DICOMwebClient
from ._utils import *

try:
    import progressbar as pg
except ImportError:
    pg = None
has_progressbar = bool(pg)

class KheopsClient:

    """
    The following keys specify the information collected in the
    summary .csv files.
    """
    STUDY_KEYS = ["StudyInstanceUID", "PatientID",
                  "StudyDate", "ModalitiesInStudy"]
    SERIES_KEYS = ["StudyInstanceUID", "SeriesInstanceUID",
                   "PatientID", "SeriesDate", "Modality", "RetrieveURL"]
    INSTANCE_KEYS = ["StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
                     "PatientID", "SeriesDate", "Modality"]
    MAX_ROWS_PRINTED = 25

    def __init__(self,
                 url,
                 access_token,
                 out_dir="downloads",
                 dry_run=False,
                 show_progress=True,
                 verbosity=0):
        self._token = self._check_token(access_token)
        self._default_out_dir = "downloads" if out_dir is None else out_dir
        self._dry_run = dry_run
        self._show_progress = show_progress
        self._client = DICOMwebClient(
            url=url,
            headers={"Authorization": "Bearer {}".format(self._token)}
        )
        self._setup_logger(verbosity=verbosity)
        self._print_status()

    def _check_token(self, token):
        if token is None:
            token = os.getenv("ACCESS_TOKEN", None)
        if not token:
            msg = (
                "ERROR: No access token was provided for the Kheops DICOM\n"
                "       repository. Use argument 'token' or the environment\n"
                "       variable ACCESS_TOKEN to set a token. About tokens:\n"
                "       https://docs.kheops.online/docs/tokens")
            print(msg)
            exit(1)
        return token

    def _setup_logger(self, verbosity):
        level = logging.WARNING
        level_ext = logging.ERROR
        verbosity = 0 if verbosity is None else verbosity
        if verbosity == 1:
            level = logging.INFO
        elif verbosity == 2:
            level = logging.DEBUG
            level_ext = logging.WARNING
        elif verbosity>= 3:
            level = logging.DEBUG
            level_ext = logging.DEBUG
        for name in ["dicomweb_client", "pydicom"]:
            _logger = logging.getLogger(name)
            _logger.setLevel(level_ext)
        self._logger = logging.getLogger("client")
        self._logger.setLevel(level)

    def _get_progress(self, size=None,
                      label="Processing...",
                      threaded=False,
                      suppress_progress=False):
        if not has_progressbar:
            class DummyBar:
                def __init__(*args, **kwargs):
                    pass
                def start(self, *args, **kwargs):
                    return self
                def update(self, *args, **kwargs):
                    return self
                def finish(self, *args, **kwargs):
                    return self
            return DummyBar()
        else:
            widgets = []
            if label:
                widgets.append(pg.FormatLabel("%-15s" % label))
                widgets.append(" ")
            if size is not None and size>0:
                digits = len(str(size))
                fmt_counter = f"%(value){digits}d/{size}"
                widgets.append(pg.Bar())
                widgets.append(" ")
                widgets.append(pg.Counter(fmt_counter))
                widgets.append(" (")
                widgets.append(pg.Percentage())
                widgets.append(")")
            else:
                widgets.append(pg.BouncingBar())
            show_bar = (self._show_progress and not suppress_progress)
            ProgressBarType = pg.ProgressBar if show_bar else pg.NullBar
            if threaded:
                from threading import Timer
                class RepeatTimer(Timer):
                    def run(self):
                        while not self.finished.wait(self.interval):
                            self.function(*self.args, **self.kwargs)
                class ThreadedProgressBar(ProgressBarType):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        self.timer = RepeatTimer(interval=0.05,
                                                 function=self.update)
                        self.timer.setDaemon(True)
                    def run(self):
                        while not self.finished.wait(self.interval):
                            self.function(*self.args, **self.kwargs)
                    def start(self, *args, **kwargs):
                        ret = super().start(*args, **kwargs)
                        self.timer.start()
                        return ret
                    def finish(self, *args, **kwargs):
                        self.timer.cancel()
                        return super().finish(*args, **kwargs)
                ProgressBarType = ThreadedProgressBar

            progress = ProgressBarType(max_value=size, widgets=widgets)
            return progress

    def _ensure_ouput_dir(self, out_dir, forced=True):
        out_dir = out_dir if out_dir is not None else self._default_out_dir
        out_dir = Path(out_dir)
        if out_dir is None:
            msg = "No output directory was specified."
            raise ValueError(msg)
        if not ensure_dir(path=out_dir, forced=forced):
            msg = "Failed to create output directory."
            raise RuntimeError(msg)
        return out_dir

    def _print_status(self):
        self._logger.info("Client configuration:")
        self._logger.info("    URL:    %s", self._client.base_url)
        self._logger.info("    Port:   %s", self._client.port)
        self._logger.info("    Token:  %s", self._token)
        self._logger.info("    Dryrun: %s", str(self._dry_run).lower())
        self._logger.info("")

    def _print_table_summary(self, df):
        empty = pd.Series(dtype=str)
        n_studies = df.get("StudyInstanceUID", empty.copy()).nunique()
        n_series = df.get("SeriesInstanceUID", empty.copy()).nunique()
        n_instances = df.get("SOPInstanceUID", empty.copy()).nunique()
        file_sizes = df.get("FileSize", empty.copy()).sum()
        modalities1 = df.get("Modality", empty.copy()).unique()
        modalities2 = df.get("ModalitiesInStudy", empty.copy())
        # modalities2 can have the following shape:
        #       [ ["CT", "XA"], "CT", ["MR", "CT"] ]
        # Note the mixing of lists and strings. To be correct: it's not
        # actually a list, it's a pydicom.multival.MultiValue.
        # Goal: Flatten the list
        #       [ "CT", "XA", "CT", "MR", "CT" ]
        def _map(x):
            if isinstance(x, str) or not hasattr(x, "__iter__"):
                return tuple([x])
            else:
                return tuple(x)
        modalities2 = modalities2.map(_map).unique()
        from itertools import chain
        modalities2 = set(chain(*modalities2))
        modalities = set(modalities1) | set(modalities2)
        modalities = list(sorted(modalities))
        print()
        print("Summary:")
        print("    Total number of studies:  ", n_studies)
        if n_series > 0:
            print("    Total number of series:   ", n_series)
        if n_instances > 0:
            print("    Total number of instances:", n_instances)
        if file_sizes > 0:
            print("    Total data siez:          ", sizeof_fmt(file_sizes))
        if modalities:
            print("    Modalities:               ", ", ".join(modalities))

    def _print_list(self, lst, label):
        lst = lst.drop_duplicates()
        print()
        print("%s:" % label)
        for s in lst[:self.MAX_ROWS_PRINTED]:
            print("    "+str(s))
        diff = len(lst)-self.MAX_ROWS_PRINTED
        if diff > 0:
            print("    ...and %d more" % diff)

    def _write_table(self, df, out_dir, label):
        if self._dry_run:
            return
        out_dir = self._ensure_ouput_dir(out_dir, forced=True)
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        filename = "{}_{}.csv".format(label, now)
        df.to_csv(out_dir/filename, index=False)
        print()
        print("Created file:")
        print("    %s" % filename)

    def _write_instances(self,
                         instances,
                         out_dir=None,
                         forced=False,
                         suppress_progress=False):
        df = dicoms_to_frame(instances, keywords=self.INSTANCE_KEYS)
        df = sort_frame_by_uid(df, by="SOPInstanceUID")
        if self._dry_run:
            return df

        out_dir = self._ensure_ouput_dir(out_dir, forced=forced)
        n = len(instances)
        progress = self._get_progress(size=n, label="Writing data...",
                                      suppress_progress=suppress_progress)
        progress.start()
        file_sizes = {}
        for i, inst in enumerate(instances):
            # type(inst): pydicom.dataset.FileDataset
            path = out_dir / inst.SeriesInstanceUID
            path /= inst.SOPInstanceUID + ".dcm"
            ensure_dir(path.parent, forced=forced)
            if not path.is_file() or forced:
                # https://pydicom.github.io/pydicom/dev/auto_examples/input_output/plot_write_dicom.html
                if inst.is_little_endian is None:
                    inst.is_little_endian = False
                if inst.is_implicit_VR is None:
                    inst.is_implicit_VR = False
                inst.save_as(path)
                bytes = path.stat().st_size
            else:
                bytes = None
                msg = "File already exists: %s" % path
                raise FileExistsError(msg)
            file_sizes[inst.SOPInstanceUID] = bytes
            progress.update(i)
        progress.finish()
        file_sizes = pd.Series(file_sizes, name="FileSize")
        file_sizes.index.name = "SOPInstanceUID"
        df = df.merge(file_sizes, left_on="SOPInstanceUID", right_index=True)
        return df

    def _query_series_for_study(self,
                                study_uid,
                                search_filters=None,
                                fuzzy=True,
                                limit=None,
                                offset=None):
        series = self._client.search_for_series(study_instance_uid=study_uid,
                                                search_filters=search_filters,
                                                fuzzymatching=fuzzy,
                                                limit=limit,
                                                offset=offset,
                                                fields=self.SERIES_KEYS)
        series = dicomize_json_results(series)
        df = dicoms_to_frame(series, keywords=self.SERIES_KEYS)
        df = sort_frame_by_uid(df, by="SeriesInstanceUID")
        return df

    def _query_series(self,
                      search_filters,
                      fuzzy=True,
                      limit=None,
                      offset=None):
        studies = self._query_studies(search_filters=search_filters,
                                      fuzzy=fuzzy,
                                      limit=limit,
                                      offset=offset)
        series = []
        progress = self._get_progress(size=len(studies),
                                      label="Fetching data...")
        for i, study_uid in enumerate(studies["StudyInstanceUID"]):
            ret = self._query_series_for_study(study_uid=study_uid,
                                               search_filters=search_filters,
                                               fuzzy=fuzzy,
                                               limit=None,
                                               offset=None)
            series.append(ret)
            progress.update(i)
        progress.finish()
        series = pd.concat(series, axis=0)
        series = sort_frame_by_uid(series, by="SeriesInstanceUID")
        return series

    def _query_studies(self,
                       search_filters=None,
                       fuzzy=True,
                       limit=None,
                       offset=None):
        studies = self._client.search_for_studies(search_filters=search_filters,
                                                  fuzzymatching=fuzzy,
                                                  limit=limit,
                                                  offset=offset,
                                                  fields=self.STUDY_KEYS)
        studies = dicomize_json_results(studies)
        df = dicoms_to_frame(studies, keywords=self.STUDY_KEYS)
        df = sort_frame_by_uid(df, by="StudyInstanceUID")
        return df

    def _retrieve_single_series(self,
                                study_uid,
                                series_uid,
                                meta_only):
        progress = self._get_progress(label="Downloading series...",
                                      threaded=True)
        progress.start()
        if meta_only:
            instances = self._client.retrieve_series_metadata(
                study_instance_uid=study_uid,
                series_instance_uid=series_uid
            )
            instances = dicomize_json_results(data=instances,
                                              meta_only=True)
        else:
            instances = self._client.retrieve_series(
                study_instance_uid=study_uid,
                series_instance_uid=series_uid
            )
        progress.finish(end="")
        return instances

    def _retrieve_single_study(self,
                               study_uid,
                               meta_only):
        progress = self._get_progress(label="Downloading study...",
                                      threaded=True)
        progress.start()
        if meta_only:
            instances = self._client.retrieve_study_metadata(
                study_instance_uid=study_uid
            )
            instances = dicomize_json_results(data=instances,
                                              meta_only=True)
        else:
            instances = self._client.retrieve_study(
                study_instance_uid=study_uid
            )
        progress.finish(end="")
        return instances

    def list_studies(self,
                     search_filters=None,
                     fuzzy=True,
                     limit=None,
                     offset=None,
                     out_dir=None):
        self._logger.info("List studies...")
        df = self._query_studies(search_filters=search_filters,
                                 fuzzy=fuzzy,
                                 limit=limit,
                                 offset=offset)
        self._print_list(lst=df["StudyInstanceUID"],
                         label="Available studies")
        self._print_table_summary(df)
        self._write_table(df=df, out_dir=out_dir,
                          label="available_studies")
        return df

    def list_series(self,
                    search_filters=None,
                    fuzzy=True,
                    limit=None,
                    offset=None,
                    out_dir=None):
        self._logger.info("List series...")
        df = self._query_series(search_filters=search_filters,
                                fuzzy=fuzzy,
                                limit=limit,
                                offset=offset)
        self._print_list(lst=df["SeriesInstanceUID"],
                         label="Available series")
        self._print_table_summary(df)
        self._write_table(df=df, out_dir=out_dir,
                          label="available_series")
        return df

    def download_series(self,
                        study_uid,
                        series_uid,
                        meta_only=False,
                        out_dir=None,
                        forced=False):
        """
        Arguments:
            out_dir:        Output directory
            meta_only:      Only write meta data, without bulk data

        Returns:
            data:           A pandas DataFrame with some DICOM keys.

        [1] https://dicomweb-client.readthedocs.io/en/latest/package.html
        """
        self._logger.info("Download single series...")
        dicoms = self._retrieve_single_series(study_uid=study_uid,
                                              series_uid=series_uid,
                                              meta_only=meta_only)
        df = self._write_instances(out_dir=out_dir,
                                   instances=dicoms,
                                   forced=forced)

        self._print_list(lst=df["SeriesInstanceUID"],
                         label="Downloaded series")
        self._write_table(df=df, out_dir=out_dir,
                          label="downloaded_series_instances")
        self._print_table_summary(df=df)
        return df

    def download_study(self, study_uid,
                       meta_only=False,
                       out_dir=None,
                       forced=False):
        self._logger.info("Download single study...")
        dicoms = self._retrieve_single_study(study_uid=study_uid,
                                             meta_only=meta_only)
        df = self._write_instances(out_dir=out_dir,
                                   instances=dicoms,
                                   forced=forced)
        self._print_list(lst=df["SeriesInstanceUID"],
                         label="Downloaded series")
        self._write_table(df=df, out_dir=out_dir,
                          label="downloaded_study_instances")
        self._print_table_summary(df=df)
        return df

    def search_and_download_studies(self,
                                    search_filters=None,
                                    meta_only=False,
                                    fuzzy=True,
                                    limit=None,
                                    offset=None,
                                    out_dir=None,
                                    forced=False):
        """
        Download all or a subset of studies.

        Arguments:
            search_filters: A dict that will be forwarded to
                           DICOMwebClient.search_for_studies(), see [1]
            meta_only:     Fetch only the DICOM meta data only (no bulk data)
            fuzzy:         Enable fuzzy search semantics
            limit:         Limit the number or results
            offset:        Number of results that should be skipped
            out_dir:       Output directory
            forced:        Do not overwrite any existing files / folders

        [1] https://dicomweb-client.readthedocs.io/en/latest/package.html
        """
        df = self._query_studies(search_filters=search_filters,
                                 fuzzy=fuzzy,
                                 limit=limit,
                                 offset=offset)
        self._logger.info("Number of studies found: %d", len(df))
        if len(df)==0:
            return
        progress = self._get_progress(size=len(df), label="Processing...")
        progress.start()
        dfs_downloaded = []
        for i, row  in df.iterrows():
            study_uid = row["StudyInstanceUID"]
            dicoms = self._retrieve_single_study(study_uid=study_uid,
                                                 meta_only=meta_only)
            progress.update(i)
            df = self._write_instances(out_dir=out_dir,
                                       instances=dicoms,
                                       forced=forced,
                                       suppress_progress=True)
            dfs_downloaded.append(df)
            progress.update(i)
        progress.finish()
        df_all = pd.concat(dfs_downloaded, axis=0)
        df_all = sort_frame_by_uid(df_all, by="SOPInstanceUID")
        self._print_list(lst=df_all["StudyInstanceUID"],
                         label="Downloaded studies")
        self._write_table(df=df_all, out_dir=out_dir,
                          label="downloaded_study_instances")
        self._print_table_summary(df=df_all)
        return df_all

    def search_and_download_series(self,
                                   search_filters=None,
                                   meta_only=False,
                                   fuzzy=True,
                                   limit=None,
                                   offset=None,
                                   out_dir=None,
                                   forced=False):
        """
        Download all or a subset of studies.

        Arguments:
            search_filters: A dict that will be forwarded to
                           DICOMwebClient.search_for_studies(), see [1]
            meta_only:     Fetch only the DICOM meta data only (no bulk data)
            fuzzy:         Enable fuzzy search semantics
            limit:         Limit the number or results
            offset:        Number of results that should be skipped
            out_dir:       Output directory
            forced:        Do not overwrite any existing files / folders

        [1] https://dicomweb-client.readthedocs.io/en/latest/package.html
        """
        df = self._query_series(search_filters=search_filters,
                                fuzzy=fuzzy,
                                limit=limit,
                                offset=offset)
        self._logger.info("Number of series found: %d", len(df))
        if len(df) == 0:
            return

        progress = self._get_progress(size=len(df), label="Processing...")
        progress.start()
        dfs_downloaded = []
        for i, row  in df.iterrows():
            study_uid = row["StudyInstanceUID"]
            series_uid = row["SeriesInstanceUID"]
            dicoms = self._retrieve_single_series(study_uid=study_uid,
                                                  series_uid=series_uid,
                                                  meta_only=meta_only)
            progress.update(i)
            df = self._write_instances(out_dir=out_dir,
                                       instances=dicoms,
                                       forced=forced,
                                       suppress_progress=True)
            dfs_downloaded.append(df)
            progress.update(i)
        progress.finish()
        df_all = pd.concat(dfs_downloaded, axis=0)
        df_all = sort_frame_by_uid(df_all, by="SOPInstanceUID")
        self._print_list(lst=df_all["SeriesInstanceUID"],
                         label="Downloaded series")
        self._write_table(df=df_all, out_dir=out_dir,
                          label="downloaded_series_instances")
        self._print_table_summary(df=df_all)
        return df_all
