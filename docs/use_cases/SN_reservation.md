# SN Reservation

Currently only implemented for modules in the module assembly step.

## Using the `SN_reservation.py` script for module assembly

When performing module assembly, you can reserve $N$ serial numbers that are available for your use case. The tool makes sure to create suitable SNs that match your prefix, and fill any potential unused counters (holes) with new SNs for you. The optional `--dryrun` argument can be useful when you just want to know what would be created (as in, this recommends the next free SNs for you, without actually storing those new parts in the DB).

Execute the following from the hgtd-tools directory (using either Anaconda Prompt or your preferred shell with which you installed miniconda or any environment with the required packages):

```shell
conda activate hgtd
python SN_reservation.py --user-name <your-user-name> --site <some-site> --prod <some-prod> --batch <some-batchNr> --n-reserve <how-many-SNs-to-reserve> (--dryrun True)
```
