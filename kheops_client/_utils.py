import time
import pandas as pd
import pydicom as dicom
from pathlib import Path

def ensure_dir(path, forced):
    path = Path(path)
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=forced)
    return path.is_dir()


def flatten(value):
    return value[0] if value is not None and len(value)==1 else value


def keyword_to_tag(keyword):
    tag = dicom.tag.Tag(keyword)
    tag = "%04X%04X" % (tag.group, tag.element)
    return tag


def extract_value(data, keyword, key="Value"):
    """
    Extract a key by its name from the DICOM dict returned by DICOMWeb.

    data:       dictionary mapping DICOM tags to its values (= inner dict)
    keyword:    name of keyword to extract
    key:        key to extract the information from the inner dict
    """
    entry = data[keyword_to_tag(keyword)]
    return flatten(entry.get(key, None))


def dicomize_json_result(data, meta_only=True):
    """
    data: dict
    """
    if meta_only:
        def handler(uri): return b""
    else:
        handler = None
    return dicom.dataset.Dataset.from_json(
        data, bulk_data_uri_handler=handler)


def dicomize_json_results(data, meta_only=True):
    """
    data: list of dict
    """
    ret = [dicomize_json_result(d) for d in data]
    return ret


def dicoms_to_frame(dicoms, keywords=None):
    """
    Convert a list of DICOM dicts (pydicom.dataset.Dataset)
    into a pandas DataFrame.

    Keywords can be a list of DICOM keywords or DICOM tags.
    The function makes use of pydicom.dataset.Dataset.get().

    By default, the following keywords are extracted:
        StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, Modality.
    """
    if keywords is None:
        # Default keywords to collect from dicoms.
        keywords = ["StudyInstanceUID",
                    "SeriesInstanceUID",
                    "SOPInstanceUID",
                    "Modality"]
    data = dict()
    for keyword in keywords:
        data[keyword] = [d.get(keyword, default=None) for d in dicoms]
    df = pd.DataFrame(data, columns=keywords)
    return df


def sort_frame_by_uid(df, by):
    def uid_key(uid):
        """
        Convert a uid into a tuple of integers.
        Example: "123.456.789" --> (123,456,789)
        """
        uid = uid.split(".")
        try:
            uid = tuple(map(int, uid))
        except ValueError as e:
            if not "invalid literal for int()" in e:
                raise
        return uid

    def sort_key(series):
        return series.apply(uid_key)

    # This requires pandas>=1.1.0
    df = df.sort_values(by=by, key=sort_key)
    return df


def sizeof_fmt(size, suffix="b"):
    """
    """
    for unit in ["", "k", "M", "G", "T", "P", "E", "Z"]:
        if abs(size) < 1024.0:
            return "%3.1f%s%s" % (size, unit, suffix)
        size /= 1024.0
    return "%.1f%s%s" % (size, "Y", suffix)


def strip_strings(df, cols=None):
    if cols is None:
        cols = df.columns
    for c in cols:
        try:
            df[c] = df[c].str.strip()
        except AttributeError:
            pass
    return df


def format_date_time(df, mode, drop=False, ignore_time_nan=False):
    """
    How the data availability is resolved:
        date:yes, time:yes      => datetime (with date and time)
        date:yes, time:no       => datetime (with date and time=00:00:00)
        date:no,  time:yes      => nan
        date:no,  time:no       => nan

    To always return nan if time:no, set the flag ignore_time_nan to True.
    """
    assert mode in ("series", "studies")
    if mode == "series":
        col_date, col_time = "SeriesDate", "SeriesTime"
        col_datetime = "SeriesDateTime"
    elif mode == "studies":
        col_date, col_time = "StudyDate", "StudyTime"
        col_datetime = "StudyDateTime"
    date = df.get(col_date, default=pd.Series(index=df.index, dtype=str))
    time = df.get(col_time, default=pd.Series(index=df.index, dtype=str))
    if ignore_time_nan:
        time = time.fillna("")
    if col_time in df:
        # Insert right of time column
        col_idx = df.columns.get_loc(col_time)+1
    else:
        # Insert at the end
        col_idx = len(df.columns)
    dt = pd.to_datetime((date+" "+time).str.strip(), errors="coerce")
    df.insert(loc=col_idx, column=col_datetime, value=dt)
    if drop:
        df = df.drop([col_date, col_time], axis=1, errors="ignore")
    return df
