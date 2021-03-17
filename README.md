# kheops-client
Python utility for querying data from a [Kheops DICOM](https://kheops.online/) database via the [DICOMWeb API](https://www.dicomstandard.org/dicomweb).

## Setup

Clone the repository and install the requirements.

```bash
git clone https://github.com/hirsch-lab/kheops-client.git
cd kheops-client
python -m pip install -r requirements.txt
```

To access a Kheops database, one requires a URL to the DICOMWeb API and an [access token](https://docs.kheops.online/docs/tokens). 

```bash
URL="https://demo.kheops.online/api"
ACCESS_TOKEN="B18jTXCzTrQzj1ZednqHUY"
OUT_DIR="./downloads"
```

Now, we are ready to use the Kheops client. 

##Usage

The tool offers two commands: `list` and `download`. 

```bash
./kheops_client_cli.py --help
./kheops_client_cli.py list --help
./kheops_client_cli.py download --help
```

### Query available studies and series

Query a list of available DICOM *studies*. A table with some information about the studies will be saved in the output directory.

```bash./kheops_client_cli.py list studies \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" ```

Query a list of available DICOM *series*. Again, a table with some information about the series will be saved in the output directory.

```bash./kheops_client_cli.py list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" ```

List the available series for a particular study by providing the `--study-uid` argument.

```bash./kheops_client_cli.py list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591"```

It is possible to constrain the query by specifying search filters. The following query requests a list of all available series with modality CT.

```bash./kheops_client_cli.py list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --search-filter "Modality" "CT" \
    --out-dir "$OUT_DIR" ```

Note that the search filters can be combined.

```bash./kheops_client_cli.py list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --search-filter "Modality" "CT" \
    --search-filter "PatientID" "FrxHK8" \
    --out-dir "$OUT_DIR" ```

On some DICOMWeb servers, the retrieved lists may be truncated due to resource limitations (a warning will be issued in that case). In that case, arguments `--limit` and `--offset` can be of help.

```bash
./kheops_client_cli.py list series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --limit 5 \
    --offset 10
```

### Download DICOM data
It is possible to download single or multiple studies/series by using the download command. 

For example, download a specific series by providing the arguments `--study-uid` and `--series-uid`. Use option `--forced` to override the data if it already exists in the output folder.

```bashpython kheops_client_cli.py download series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591" \
    --series-uid "1.2.840.113704.1.111.5692.1127829280.6" \
    --forced```

To download all series in a study, just omit the argument `--series-uid`.

```bashpython kheops_client_cli.py download series \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591" \
    --forced```

Detail: This is pretty much equivalent to 

```bashpython kheops_client_cli.py download studies \
    --url "$URL" \
    --token "$ACCESS_TOKEN" \
    --out-dir "$OUT_DIR" \
    --study-uid "2.16.840.1.113669.632.20.1211.10000098591" \
    --forced```

#### Further arguments/options
- For testing, it may be useful to limit the maximum number of studies and to specify an offset: `--limit` and `--offset`
- Option `--dry-run` runs the commands without writing any output data
- Option `--meta-only` permits to download only the DICOM data structure without any bulk data.
- Control the verbosity level by using the flag `--verbosity` multiple times. Or by using the short form: `-v`, `-vv`, `-vvv`.



## Further reading
[DICOM standard](https://www.dicomstandard.org/current)  
[DICOM dictionary browser](https://dicom.innolitics.com/ciods)  
[DICOMWeb standard](https://www.dicomstandard.org/dicomweb)  
[Pydicom](https://pydicom.github.io/) ([docs](https://pydicom.github.io/pydicom/stable/), [api docs](https://dicomweb-client.readthedocs.io/en/latest/package.html#), [github](https://github.com/pydicom/pydicom))   
[DICOMWeb client for python](https://dicomweb-client.readthedocs.io/en/latest/) ([github](https://github.com/mghcomputationalpathology/dicomweb-client))
