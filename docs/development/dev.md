# Developer overview
## Reusing the included API module
The `api.py` module can be used standalone as well to make API requests to the HGTD Production Database. Note that the included functions also return the response `status_code` and `reason` and handle a variety of possible errors.

The basic types of requests are:

- **GET**: without payload, fetch some specified record/view etc.
- **POST**: sends a payload (dictionary as json, or more involved types like a tar for measurement data, with another dictionary for human-readable requests)
- **DELETE**: without payload, remove some record

Those three variants are implemented as `api.fetch_information`, `api.post_information`, `api.delete_information` handling the endpoint, headers etc. for you so you don't have to worry about anything besides the actual information received, posted or deleted.

### REST API HTTP Status Codes 101

Please refer to this overview of the most common status codes and what you can learn from them:

- **Starts with 2**: good news, wohoo! Your request was successful, e.g. retrieving data (200) or creating new data upstream (201).
- **Starts with 4**: you sure what you are doing is correct? Likely a typo or bad payload in your request (400) when the endpoint exists, but it does not like your request, or missing authentication / access token (401). Could also be wrong URL (404) which is similar to dialing a phone number that does not exist ("The number you have dialed is not in service.", but in the web edition).
- **Starts with 5**: server has received your request, but failed to process it internally. Can be an error that is not caught, e.g. the python-portion of our backend had an error while processing (500), not further specified where and what went wrong. Could also be something related to DB / some infrastructure not available or overloaded (502 / 503), or your request taking too long / timeout (504).

More codes and their explanation are documented for example over at [wikipedia](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes){target="_blank"}.

### Worked out standalone example and the API client in action
Have a look at the notebook `example_API_usage.ipynb` to see the included API module in action. The notebook shows two use cases for user interaction with the DB that can be implemented as part of scripts (as in FADAPro, for example): adding a value for a single attribute (useful for e.g. module metrology) or complete bulk upload of a tar containing various files (useful for e.g. module electrical measurements). For proper authentication, these steps to get started are included as well.

The interface to FADAPro is implemented in the [MR](https://gitlab.cern.ch/atlas-hgtd/Electronics/fadapro/-/merge_requests/9){target="_blank"}, documented in [FADAPro docs on `DB_interface.py`](https://hgtd-fadapro.docs.cern.ch/commandlist/#upload-to-database){target="_blank"}.

Flex tail measurement uploads are implemented [with the CLI script `upload_FlexTail_measurements.py`](../use_cases/FT_upload_instructions.md).

## pre-commit

We use some standard pre-commit hooks (see `.pre-commit-config.yaml`). If you want to setup this helpful tool as well:

```shell
pre-commit install
```

And you can run the hooks on all files by

```shell
pre-commit run --all-files
```

## Contributing

If you are developing features yourself or want to resolve an issue, please [Fork](https://gitlab.cern.ch/anstein/hgtd-tools/-/forks/new){target="_blank"} this repository and then submit a [Merge Request](https://gitlab.cern.ch/anstein/hgtd-tools/-/merge_requests/new){target="_blank"} to the [master branch](https://gitlab.cern.ch/anstein/hgtd-tools){target="_blank"}. Add `anstein` as a member of your private fork with at least `Reporter` rights, such that during MR review, your reviewer can see the pipelines in your fork. If you give `Developer` rights, this will allow `anstein` to also push co-authored commits into your development-branch to ease the MR review and merging.

We run a set of basic pre-commit checks for your MR, so be prepared to modify the changed files according to the `.gitlab-ci.yaml` pipeline before your MR can be merged. Test your changes locally before pushing (and avoid using unneccessary CI time + core-h), using the instructions outlined in the pre-commit paragraph.

Not every minor commit needs to trigger a CI pipeline, for example clerical changes or something that only affects documentation but no logic. In that case, please adapt your regular commit message as follows to skip the CI for a specific commit:

```bash
git commit -m 'here is my regular commit message [skip ci]'
```

(note the `[skip ci]` flag).

## New version policy and process
The procedure for tagging new versions of this software is outlined in [procedure_new_release](procedure_new_release.md).

## Dockerization (discontinued)
A deployment of this app to CERN OKD using docker was attempted, but discontinued because of difficulties getting the graphical part running and deploying the same, while now practically all users are comfortable using the tools standalone on their device. Local docker containers were running well on test platforms (e.g. lxplus with `ssh -XY`), however, due to security measures, buttons that bring you to a special URL in your system's browser were blocked. The instructions for docker development are therefore archived under [docker](docker.md) and will not be continued.
