# kheops-client
Utility for querying data from a [Kheops DICOM](https://kheops.online/) database via the [DICOMWeb API](https://www.dicomstandard.org/dicomweb).

## Setup
Install the Python package and command line utility using pip:

```bash
python -m pip install kheops-client
```

Alternatively, the package can be built and installed from source:

```bash
git clone https://github.com/hirsch-lab/kheops-client.git
cd kheops-client
python setup.py sdist
python -m pip install dist/kheops-client*.tar.gz
```

## Usage

To access a Kheops database, one requires a URL to the DICOMWeb API and an [access token](https://docs.kheops.online/docs/tokens). The examples below make use of the following variables:

```bash
URL="https://demo.kheops.online/api"
ACCESS_TOKEN="B18jTXCzTrQzj1ZednqHUY"
OUT_DIR="./downloads"
```

The tool offers two commands: `list` and `download`.

```bash
kheops-client --help
kheops-client list --help
kheops-client download --help
```

### Query available studies and series

Query a list of available DICOM *studies*. A table with some information about the studies will be saved in the output directory.

```bash
kheops-client list studies \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR"
```

Query a list of available DICOM *series*. Again, a table with some information about the series will be saved in the output directory.

```bash
kheops-client list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR"
```

List the available series for a particular study by providing the `--study-uid` argument.

```bash
kheops-client list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591"
```

It is possible to constrain the query by specifying search filters. The following query requests a list of all available series with modality CT.

```bash
kheops-client list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --search-filter "Modality" "CT" \
    --out-dir "$OUT_DIR"
```

Note that the search filters can be combined.

```bash
kheops-client list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --search-filter "Modality" "CT" \
    --search-filter "PatientID" "FrxHK8" \
    --out-dir "$OUT_DIR"
```

On some DICOMWeb servers, the retrieved lists may be truncated due to resource limitations (a warning will be issued in that case). In that case, arguments `--limit` and `--offset` can be of help.

```bash
kheops-client list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --limit 5 \
    --offset 10
```

### Download DICOM data
It is possible to download single or multiple studies/series by using the download command.

For example, download a specific series by providing the arguments `--study-uid` and `--series-uid`. Use option `--forced` to override the data if it already exists in the output folder.

```bash
kheops-client download series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591" \
    --series-uid "1.2.840.113704.1.111.5692.1127829280.6" \
    --forced
```

To download all series in a study, just omit the argument `--series-uid`.

```bash
kheops-client download series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591" \
    --forced
```

Detail: This is pretty much equivalent to

```bash
kheops-client download studies \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591" \
    --forced
```

#### Further arguments/options
- For testing, it may be useful to limit the maximum number of studies and to specify an offset: `--limit` and `--offset`
- Option `--dry-run` runs the commands without writing any output data
- Option `--meta-only` permits to download only the DICOM data structure without any bulk data.
- Control the verbosity level by using the flag `--verbosity` multiple times. Or by using the short form: `-v`, `-vv`, `-vvv`.

### Python API
The above functionality is implemented in [KheopsClient](https://github.com/hirsch-lab/kheops-client/blob/main/kheops_client/client.py).

```python
client = KheopsClient(url="URL", access_token="ACCESS_TOKEN")
client.list_studies(...)
client.list_series(...)
client.download_study(...)
client.download_series(...)
client.search_and_download_studies(...)
client.search_and_download_series(...)
```


## Further reading
[DICOM standard](https://www.dicomstandard.org/current)
[DICOM dictionary browser](https://dicom.innolitics.com/ciods)
[DICOMWeb standard](https://www.dicomstandard.org/dicomweb)
[Pydicom](https://pydicom.github.io/) ([docs](https://pydicom.github.io/pydicom/stable/), [api docs](https://dicomweb-client.readthedocs.io/en/latest/package.html#), [github](https://github.com/pydicom/pydicom))
[DICOMWeb client for python](https://dicomweb-client.readthedocs.io/en/latest/) ([github](https://github.com/mghcomputationalpathology/dicomweb-client))
