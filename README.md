# Towards ML-KEM & ML-DSA on OpenTitan

This repository is a fork of the official [OpenTitan
repository](https://github.com/lowRISC/opentitan/) extended with changes to the
hardware design as well as the Python simulator for OTBN in order to provide
support for ML-KEM & ML-DSA. It accompanies the paper titled "Towards ML-KEM &
ML-DSA on OpenTitan". 

All software and hardware described in this paper will be made publicly
available under permissive licenses compatible to the OpenTitan license. At this
time, we are still preparing for their final publication. However, you can find
the code in the state of the submission of the paper (11/2024) under [this
link](https://drive.proton.me/urls/5505QX8SX0#ndJGQEdzXodZ).

In the following, we will give a description to guide the reader on how to
re-run our tests and reproduce the results.

## Getting started
For setting up the software and testing environment, we generally refer to the
[guide by the OpenTitan
team](https://opentitan.org/guides/getting_started/index.html). 

We made good experiences with the setup using Docker on macOS and Linux.

In the case you are using Docker and managed to build and enter the container as
described
[here](https://github.com/lowRISC/opentitan/tree/master/util/container) (from
one of the submodules), execute the following
steps:
```
# Installing python dependencies.
sudo apt install python3.8-venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip "setuptools<66.0.0"
pip3 install -r python-requirements.txt

git config --global --add safe.directory /home/dev/src
```

Now, you are all set up to run the tests as described below. 

## Relevant files

Our implementation modeling the `bn.mulv{m}` instruction as a multi-cycle one
can be found in the submodule TODO, while the one
taking just one cycle can be found in TODO.
These are also the two submodules containing the modified simulator. The submodule
TODO contains the hardware design only modified to
include the KMAC/OTBN interface. TODO contains the ASIC
synthesis scripts to use with Cadence.

Our modifications to the ISA and the Python simulator are mainly reflected in
the following files:
- `hw/ip/otbn/dv/otbnsim/sim/insn.py`: This file contains the Python semantics
  of the OTBN instructions. Here we define the operation for our added
  instructions.
- `hw/ip/otbn/data/bignum-insns.yml`: In this file, we give the definition of
  our instruction in a machine-readable way such that it can be automatically
  picked up by the OpenTitan toolchain.
- `hw/ip/otbn/data/enc-schemes.yml`: The encoding scheme for our newly added
  instructions is defined in this file. 

With respect to the software implementations of ML-KEM & ML-DSA, the relevant
files can be found under `sw/otbn/crypto/handwritten` for ML-DSA, under
`sw/otbn/crypto/kyber-handwritten` for ML-KEM, and the tests for the
implementations can be found under `sw/otbn/crypto/tests`. Files containing
`_plain_` in their names refer to the implementation on OTBN, files containing
`_base_` refer to the implementation on OTBN^{KMAC}. Files containing no such
annotation are either shared or relevant to the implementation on
OTBN^{KMAC}_{Ext.}.

The most important tests are the ones interfacing to Python implementations of
ML-KEM & ML-DSA. Mainly, the files
`sw/otbn/crypto/tests/dilithiumpy_bench_otbn/bench_dilithium.py` and
`sw/otbn/crypto/tests/kyberpy_bench_otbn/bench_kyber.py` allow for configuring
the test, i.e., setting the number of threads to use (`NPROC`) and the number of
iterations to run `ITERATIONS`. The `DATABASE_PATH` defines the location to
which an sqlite database with the benchmark results will be written to. 

## Running the performance benchmarks
In order to run the tests/benchmarks, the
following commands are used:

**For ML-DSA**:
```
./bazelisk.sh test --test_timeout=10000 --copt="-DDILITHIUM_MODE={2,3,5}" --cache_test_results=no --sandbox_writable_path="/home/dev/src" //sw/otbn/crypto/tests:dilithium{2,3,5}_{key_pair,sign,verify}{_,_plain_,_base_}bench
```
This command offers multiple degrees of freedom:
1. The parameter set 2, 3, or 5 can be chosen.
2. It can be chosen which algorithm to run (key_pair, sign, verify).
3. Selecting between three different variants of the implementation. Using `_`
   between the algorithm to run and `bench` selects the implementation using the
   ISA extensions and KMAC interface. Using `_base_` uses just the KMAC
   interface and `_plain_` solely relies on OTBN's capabilities as they were
   given.
4. `sandbox_writable_path` needs to be set to the path, to which the database
   file should be written, i.e., the path from `DATABASE_PATH`. This is required
   to escape the bazel sandbox.
5. `timeout` Depending on the selected test and the number of iterations, an
   appropriate timeout should be set. Note that a single test (esp. signing) can
   take up to multiple minutes. 

Example: 
```
./bazelisk.sh test --test_timeout=10000 --copt="-DDILITHIUM_MODE=2" --cache_test_results=no --sandbox_writable_path="/home/dev/src" //sw/otbn/crypto/tests:dilithium2_key_pair_bench
```

**For ML-KEM**:
```
./bazelisk.sh test --test_timeout=1000 --copt="-DKYBER_K={2,3,4}" --cache_test_results=no --sandbox_writable_path="/home/dev/src" //sw/otbn/crypto/tests:mlkem{512,768,1024}_{keypair,encap,decap}{_,_plain_,_base_}bench
```
The parameters to choose from for the ML-KEM command are highly similar to the
ones for ML-DSA.

Example: 
```
./bazelisk.sh test --test_timeout=1000 --copt="-DKYBER_K=4" --cache_test_results=no --sandbox_writable_path="/home/dev/src" //sw/otbn/crypto/tests:mlkem1024_decap_bench
```

The script `Evaluation_clean.py` can be used to analyze the database and
evaluate the collected data.

### Data used in the paper
In addition to the code, we also upload our own databases in which we collected
the benchmarks. The databases are contained in the archive DBs.zip. The naming
scheme inside the DBs is coherent with the ones of the tests. The files are
named after the OTBN variants from the paper. The following files contain the
data:

- `dilithium_bench_OTBN-KMAC-Ext.db`: This file contains the ML-DSA
  benchmarks for our ISA-extended variant of OTBN with the KMAC interface. The
  respective benchmark ids are 1-9.
- `dilithium_bench_OTBN_OTBN-KMAC_OTBN-KMAC-Ext++.db`: This file contains the
  ML-DSA benchmarks for the plain OTBN, OTBN with just the KMAC interface,
  and OTBN with our ISA extensions where the `bn.mulv{m}` instruction terminates
  in a single cycle. The respective benchmark ids are 37-63.
- `mlkem_bench_OTBN-KMAC-Ext.db`: This file contains the ML-KEM
  benchmarks for our ISA-extended variant of OTBN with the KMAC interface. The
  respective benchmark ids are 1-9.
- `mlkem_bench_OTBN_OTBN-KMAC_OTBN-KMAC-Ext++.db`: This file contains the
  ML-KEM benchmarks for the plain OTBN, OTBN with just the KMAC interface,
  and OTBN with our ISA extensions where the `bn.mulv{m}` instruction terminates
  in a single cycle. The respective benchmark ids are 1-18 and 23-33.

These files can be processed by `Evaluation_clean.py` in order to obtain the
results in a readable format.

## Stack usage benchmark
The means for obtaining the stack benchmarks can be enabled by setting
`STACK_BENCH` in `hw/ip/otbn/dv/otbnsim/sim/insn.py` to `True`. This way, a file
`/home/dev/src/stack_bench.txt` (adapt if required) will be read/written which
keeps track of the stack size in the current execution. For this, also set
`STACK_SIZE` to the value as it is defined in the respective test under
`sw/otbn/crypto/tests` (e.g., `sign_dilithium_test.s`). The values in question
are 128000 for ML-DSA and 20000 for ML-KEM.

## Code size benchmarks
We provide the full-scheme binary builds for ML-KEM and ML-DSA in
`sw/otbn/crypto/tests` under the name `{mldsa, mlkem}_{plain_,base_}test.s`. In
order to obtain the `.elf` output file, the following command is used: For
ML-KEM:
```
./bazelisk build --copt="-DKYBER_K={2,3,4}" //sw/otbn/crypto/tests:mlkem{_,_plain_,_base_}codesize
```
Then to obtain the code size, we run `size` on the respective
`mlkem_{_,_base_,_plain_}codesize.elf` file:
```
size //path/to/binary/file/mlkem_{_,_base_,_plain_}codesize.elf
```
We note that to choose which security level for ML-KEM, the `KYBER_K` parameter
must be set in the command line above. Then as there is only one binary output
file, the `size` command must be called after. 

For ML-DSA: 
The steps are similar for those of ML-KEM, with the following
commands:
```
./bazelisk build --copt="-DDILITHIUM_MODE={2,3,5}" //sw/otbn/crypto/tests:mldsa{_,_plain_,_base_}codesize
size //path/to/binary/file/mldsa_{_,_base_,_plain_}codesize.elf

```

## Hardware Synthesis
We use FuseSoC to generate the necessary build scripts for different targets and tools. The following command generates scripts for the target ${TARGET} of the ip ${IP} for the tool ${TOOL}.
```
fusesoc --cores-root . run --flag=fileset_top --target=${TARGET} --no-export --tool=${TOOL} --setup ${IP}
```
To evaluate our extensions, we added different targets to various ip and synthesized them with Vivado and Genus.

### FuseSoC Commands for OTBN Targets

#### BN-ALU
```
fusesoc --cores-root . run --flag=fileset_top --target=syn_bn_alu --no-export --tool=${TOOL} --setup=lowrisc:ip:otbn:0.1
```

#### BN-MAC
```
fusesoc --cores-root . run --flag=fileset_top --target=syn_bn_mac --no-export --tool=${TOOL} --setup=lowrisc:ip:otbn:0.1
```

#### BN-MULV

```
fusesoc --cores-root . run --flag=fileset_top --target=syn_bn_mulv --no-export --tool=${TOOL} --setup=lowrisc:ip:otbn:0.1
```

#### OTBN
```
fusesoc --cores-root . run --flag=fileset_top --target=syn --no-export --tool=${TOOL} --setup=lowrisc:ip:otbn:0.1
```

### FuseSoC Commands for Top-Earlgrey FPGA Target

#### CW310
```
fusesoc --cores-root . run --flag=fileset_top --target=synth --no-export --setup lowrisc:systems:chip_earlgrey_cw310
```

#### CW340
```
fusesoc --cores-root . run --flag=fileset_top --target=synth --no-export --setup lowrisc:systems:chip_earlgrey_cw340
```

### FuseSoC Commands for Top-Earlgrey ASIC Target

```
fusesoc --cores-root . run --flag=fileset_top --target=syn --tool=genus --no-export --setup lowrisc:systems:chip_earlgrey_asic
```
Note, that due to missing standard-cells in the ASAP7 PDK, our synthesis script will target the top_earlgrey design rather than the chip-earlgrey-asic design.

### Synthesis with Vivado
FuseSoC automatically generates all necessary scripts to run synthesis with Vivado. To evaluate the different targets and run synthesis run the following commands:
```
cd ${REPO_TOP}/build/${IP}/${TARGET}-${TOOL}
vivado -mode tcl 
source lowrisc-ip-otbn-0.1.tcl
source lowrisc-ip-otbn-0.1._synth.tcl

```

### Synthesis with Genus and ASAP7
To enable Genus for FuseSoC, it is necessary to install a specific version of edalize manually:
```
git clone https://github.com/olofk/edalize
git checkout origin/dcgenus
cd edalize
pip3 install --user -r dev-requirements.txt
pre-commit install
pip3 install --user -e .

```

FuseSoC then automatically generates some basic scripts which call custom scripts which have to be development by oneself. We created scripts to run ASIC synthesis with Cadence Genus and the ASAP7 PDK. These scripts reside within *hw/syn/tools/genus* and *hw/ip/otbn/syn*. To use these scripts please install the ASAP7 PDK and adapt all paths (ASAP-7 PDK directory and ${REPO_TOP}) accordingly.

To evaluate different targets and run synthesis with Cadence Genus run the following commands:
```
cd ${REPO_TOP}/build/${IP}/${TARGET}-${TOOL}
make
```
