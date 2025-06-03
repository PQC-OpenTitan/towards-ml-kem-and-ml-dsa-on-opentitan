# Towards ML-KEM & ML-DSA on OpenTitan

This repository is a fork of the official [OpenTitan
repository](https://github.com/lowRISC/opentitan/) extended with changes to the
hardware design as well as the Python simulator for OTBN in order to provide
support for ML-KEM & ML-DSA. It accompanies the paper [Towards ML-KEM & ML-DSA
on OpenTitan](https://eprint.iacr.org/2024/1192). In the following, we will give
a description to guide the reader on how to re-run our tests and reproduce the
results.

## Getting started
For setting up the software and testing environment, we generally refer to the
[guide by the OpenTitan
team](https://opentitan.org/guides/getting_started/index.html). 

We made good experiences with the setup using Docker on macOS and Linux for
running the tests and benchmarks using the Python simulator, as well as running
the hardware design using Verilator. Running tests on an FPGA requires a setup
on a native, Linux-based system as the container is not meant to be used for
this. 

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

In addition to that, it is required to make one manual modification to resolve
an issue with the dependencies of the OpenTitan repositories. Running the
following will fail but the directory structure of the build systems's cache
which is required to proceed with the setup. This is required for the Docker
setup as well as the native one:

```
./bazelisk.sh test //sw/otbn/crypto/tests:ed25519_ext_add_test
```

After that, copy the two files `aux/bazel.py` and `aux/wheel.py` from this repository to
`~/.cache/bazel/_bazel_<USER>/<HASH>/external/rules_python/python/pip_install/extract_wheels/lib`
in the docker container/on your machine. 

Now, you are all set up to run the tests as described below. 

## Relevant files
We provide 4 submodules for our implementations:
- The submodule [towards-mlkem-and-mldsa-on-opentitan-dev-multi-cycle-bnmulv](https://github.com/PQC-OpenTitan/towards-ml-kem-and-ml-dsa-on-opentitan-dev-multi-cycle-bnmulv/tree/c2f2d734ea1d7dd56c6c54f6b8f4934cccc60943) models the `bn.mulv{m}` instruction as
a multi-cycle one.
- The submodule [towards-mlkem-and-mldsa-on-opentitan-dev-single-cycle-bnmulv](https://github.com/PQC-OpenTitan/towards-ml-kem-and-ml-dsa-on-opentitan-dev-single-cycle-bnmulv/tree/ec24f87963e88a22091ce84dfe30069d3ed8dc28) models the `bn.mulv{m}` instruction as
a single cycle one.
- The submodule
[towards-mlkem-and-mldsa-on-opentitan-dev-kmac-only](https://github.com/PQC-OpenTitan/towards-ml-kem-and-ml-dsa-on-opentitan-dev-kmac-only/tree/031eb34126c2ad1253bda0b02b300a5e99fd0e58)
contains only the hardware changes for the KMAC interface.
- The submodule
[towards-mlkem-and-mldsa-on-opentitan-ref-synth](https://github.com/PQC-OpenTitan/towards-ml-kem-and-ml-dsa-on-opentitan-ref-synth/tree/9845efc941acb46869498ca256763b9a12dfe7a0)
contains the ASIC synthesis scripts to use with Cadence.

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
./bazelisk.sh test --test_timeout=1000 --copt="-DKYBER_K={2,3,4}" --cache_test_results=no --sandbox_writable_path="/home/dev/src" //sw/otbn/crypto/tests:mlkem{512,768,1024}{_,_plain_,_base_}{keypair,encap,decap}_bench
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
are:
- 20000 for ML-KEM (Keypair, Encapsulation, Decapsulation)
- 112000 for ML-DSA Keypair and Verify
- 51200 for ML-DSA-44 Sign
- 78848 for ML-DSA-65 Sign
- 120832 for ML-DSA-87 Sign


## Code size benchmarks
We provide the full-scheme binary builds for ML-KEM and ML-DSA in
`sw/otbn/crypto/tests` under the name `{mldsa, mlkem}_{plain_,base_}test.s`. In
order to obtain the `.elf` output file, the following command is used:

**For ML-KEM**:
```
./bazelisk.sh build --copt="-DKYBER_K={2,3,4}" //sw/otbn/crypto/tests:mlkem{_,_plain_,_base_}codesize
```
Then to obtain the code size, we run `size` on the respective
`mlkem_{_,_base_,_plain_}codesize.elf` file:
```
size //path/to/binary/file/mlkem_{_,_base_,_plain_}codesize.elf
```
We note that to choose which security level for ML-KEM, the `KYBER_K` parameter
must be set in the command line above. Then as there is only one binary output
file, the `size` command must be called after. 

**For ML-DSA**:

The steps are similar for those of ML-KEM, with the following commands:
```
./bazelisk.sh build --copt="-DDILITHIUM_MODE={2,3,5}" //sw/otbn/crypto/tests:mldsa{_,_plain_,_base_}codesize
size //path/to/binary/file/mldsa_{_,_base_,_plain_}codesize.elf
```

## Hardware Synthesis
We use FuseSoC to generate the necessary build scripts for different targets and tools. The following command generates scripts for the target ${TARGET} of the ip ${IP} for the tool ${TOOL}.
```
fusesoc --cores-root . run --flag=fileset_top --target=${TARGET} --no-export --tool=${TOOL} --setup ${IP}
```
To evaluate our extensions, we added different targets to various IP and synthesized them with Vivado and Genus.

### FuseSoC Commands for OTBN Targets

#### BN-ALU
```
fusesoc --cores-root . run --flag=fileset_top --target=syn_bn_alu --no-export --tool=${TOOL} --setup lowrisc:ip:otbn:0.1
```

#### BN-MAC
```
fusesoc --cores-root . run --flag=fileset_top --target=syn_bn_mac --no-export --tool=${TOOL} --setup lowrisc:ip:otbn:0.1
```

#### BN-MULV

```
fusesoc --cores-root . run --flag=fileset_top --target=syn_bn_mulv --no-export --tool=${TOOL} --setup lowrisc:ip:otbn:0.1
```

#### OTBN
```
fusesoc --cores-root . run --flag=fileset_top --target=syn --no-export --tool=${TOOL} --setup lowrisc:ip:otbn:0.1
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
FuseSoC then automatically generates some basic scripts which call custom scripts which have to be development by oneself. We created scripts to run ASIC synthesis with Cadence Genus and the ASAP7 PDK. These scripts reside within `hw/syn/tools/genus` and `hw/ip/otbn/syn`. To use these scripts please install the ASAP7 PDK and adapt all paths (ASAP-7 PDK directory and ${REPO_TOP}) accordingly.

To evaluate different targets and run synthesis with Cadence Genus run the following commands:
```
cd ${REPO_TOP}/build/${IP}/${TARGET}-${TOOL}
make
```

## UVM Verification
Our hardware extensions for the OTBN are verified within OpenTitan's UVM framework with Cadence Xcelium as simulator. OTBN's testbench uses a DPI-based OTBN model which wraps the Python ISA simulator as subprocess. This allows to verify that the RTL-code of the OTBN behaves the same as the Python ISA simulator. To run the verification of the extended ISA, the following command can be used:

```
util/dvsim/dvsim.py hw/ip/otbn/dv/uvm/otbn_sim_cfg.hjson -i pq --verbose
```

The above command automatically runs a list of tests, namely: `otbn_bnmulv`, `otbn_bnmulvl`, `otbn_bnmulvm`, `otbn_bnmulvml`, `otbn_bnaddv`, `otbn_bnaddvm`, `otbn_bnshv`, `otbn_bntrn`, `otbn_smoke`.
While `otbn_smoke` verifies the original ISA, the other tests verify our ISA extensions. More details about design verification of the OTBN can be found under [here](https://opentitan.org/book/hw/ip/otbn/dv/index.html#otbn-dv-document).

## FPGA Validation
Our hardware extensions for the OTBN^{KMAC}\_{Ext} implementation have been validated
on the CW310 platform. However, the OTBN^{KMAC}\_{Ext++} design exceeds the
resource capacity of the CW310 and can only be executed on the CW340.
Additionally, due to the version of OpenTitan on which our project is based, the
CW340 does not fully support running software with the Bazel toolchain. To work
around this limitation, software must be built in a separate repository using a
modified Python simulator, and the resulting binaries are then used within our
repository to run on the CW340. Therefore, our testing instructions are limited
to the CW310 platform. We will address this issue and update the instructions.

After setting up the connection of the board with your PC (following this
[guide](https://opentitan.org/book/doc/getting_started/setup_fpga.html#detecting-the-pc-connections-to-the-boards)),
you can load the bitstream which resides in ${REPO_TOP}/hw/bitstream/cw310 with
the following command:
```
./bazelisk.sh run //sw/host/opentitantool -- fpga load-bitstream ${REPO_TOP}/hw/bitstream/cw310/lowrisc_systems_chip_earlgrey_cw310_0.1.bit 
```

### ISA Validation
To build the bitstream and verify the extended ISA on the CW310, run the command below. To skip the bitstream build, use `--define bitstream=skip`:
```
./bazelisk.sh test --define bitstream=skip --cache_test_results=no --test_output=streamed //sw/device/tests:otbn_isa_ext_test_fpga_cw310_test_rom
```

The above test runs a list of tests on the OTBN and either verifies the output against known testvectors, or computes the reference operation on the main processor (Ibex) and verifies OTBN's output against the reference Ibex implementation.

### KMAC Interface
To verify the KMAC interface on the CW310, run the following command:
```
./bazelisk.sh test --define bitstream=skip --cache_test_results=no --test_output=streamed //sw/device/tests:otbn_kmac_smoketest_fpga_cw310_test_rom
```

### ML-KEM Validation
The FPGA tests for ML-KEM {keypair, encap, decap} are structured as follows:
1. The C reference implementation of an operation (keypair, encap, or decap) from
   [pq-crystals/kyber](https://github.com/pq-crystals/kyber) is run.
2. The plain implementation (OTBN) of the corresponding operation of ML-KEM is
   run. The result is compared with the C results.
3. The base implementation (OTBN^{KMAC}) of the corresponding operation of ML-KEM is
   run. The result is compared with the C results.
4. The ISAEXT implementation (OTBN^{KMAC}_{Ext}) of the corresponding operation
   of ML-KEM is run. The result is compared with the C results.

To run these tests on CW310, use the following command with the correct parameters:
```
./bazelisk.sh test --define  bitstream=skip --copt="-DKYBER_K={2,3,4}" --test_output=streamed //sw/device/tests:otbn_mlkem_{keypair,encap,decap}_test_fpga_cw310_test_rom
```

### ML-DSA Validation
The FPGA tests for ML-DSA {keypair, sign, verify} are structured very similarly
to those of Ml-KEM:
1. The C reference implementation of an operation (keypair, sign, or verify) from
   [lowram](https://github.com/dop-amin/dilithium/tree/lowram) is run.
2. The plain implementation (OTBN) of the corresponding operation of ML-DSA is
   run. The result is compared with the C results.
3. The base implementation (OTBN^{KMAC}) of the corresponding operation of ML-DSA is
   run. The result is compared with the C results.
4. The ISAEXT implementation (OTBN^{KMAC}_{Ext}) of the corresponding operation
   of ML-DSA is run. The result is compared with the C results.

To run these tests on CW310, use the following command with the correct parameters:
```
./bazelisk.sh test --define  bitstream=skip --copt="-DDILITHIUM_MODE={2,3,5}" --test_output=streamed //sw/device/tests:otbn_mldsa_{keypair,sign,verify}_test_fpga_cw310_test_rom
```

## Verilator Validation
All the tests mentioned in **FPGA Validation** can be simulated in Verilator,
with the following commands:

### ISA Validation
```
./bazelisk.sh test --cache_test_results=no --test_output=streamed --test_timeout=100000 //sw/device/tests:otbn_isa_ext_sim_verilator
```

### KMAC Interface
```
./bazelisk.sh test --cache_test_results=no --test_output=streamed --test_timeout=100000 //sw/device/tests:otbn_kmac_smoketest_sim_verilator
```

### ML-KEM Validation
```
./bazelisk.sh test --copt="-DKYBER_K={2,3,4}" --test_output=streamed --test_timeout=100000 //sw/device/tests:otbn_mlkem_{keypair,encap,decap}_test_sim_verilator
```

### ML-DSA Validation
```
./bazelisk.sh test --copt="-DDILITHIUM_MODE={2,3,5}" --test_output=streamed --test_timeout=100000 //sw/device/tests:otbn_mldsa_{keypair,sign,verify}_test_sim_verilator
```

## Questions
The software modifications were done by 
Amin Abdulrahman (amin@abdulrahman.de) and
Hoang Nguyen Hien Pham (nguyenhien.phamhoang@gmail.com).
The hardware modifications were done by
Tobias Stelzer (tobias.stelzer@aisec.fraunhofer.de) and
Felix Oberhansl (felix.oberhansl@aisec.fraunhofer.de). Please let us know if you
need help or have any questions.

## Bibliography
When referring to this work, please consider using the following bibTeX excerpt:
```
@INPROCEEDINGS {,
author = { Abdulrahman, Amin and Oberhansl, Felix and Pham, Hoang Nguyen Hien and Philipoom, Jade and Schwabe, Peter and Stelzer, Tobias and Zankl, Andreas },
booktitle = { 2025 IEEE Symposium on Security and Privacy (SP) },
title = {{ Towards ML-KEM & ML-DSA on OpenTitan }},
year = {2025},
volume = {},
ISSN = {2375-1207},
pages = {4044-4062},
doi = {10.1109/SP61157.2025.00220},
url = {https://doi.ieeecomputersociety.org/10.1109/SP61157.2025.00220},
publisher = {IEEE Computer Society},
address = {Los Alamitos, CA, USA},
month =May}
```