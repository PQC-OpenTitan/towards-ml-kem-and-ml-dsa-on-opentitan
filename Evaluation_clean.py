import sqlite3
import argparse
from operator import add
from collections import defaultdict
from typing import List
from statistics import mean, median, stdev
from tabulate import tabulate

# Select algorithm to evaluate
ALGO = "dilithium"

# Enable this when evaluating benchmarks from OTBN^{KMAC}_{Ext.++} in order to
# distinguish the names.
HIGHSPEED = False
if HIGHSPEED:
    highspeed_label = "_highspeed"
else:
    highspeed_label = ""

if ALGO == "dilithium":
    _GROUPING = {
        "Polynomial Arithmetic": ["intt_base_dilithium", "ntt_base_dilithium", "poly_pointwise_acc_base_dilithium", "poly_pointwise_base_dilithium", "poly_sub_base_dilithium", "poly_add_base_dilithium", "poly_add_pseudovec_base_dilithium", "poly_pointwise_acc_dilithium", "intt_dilithium", "ntt_dilithium", "poly_pointwise_dilithium", "poly_add_dilithium", "poly_sub_dilithium"],
        "Reduction": ["poly_reduce32_pos_dilithium", "poly_reduce32_dilithium", "poly_reduce32_short_dilithium", "poly_caddq_base_dilithium", "poly_caddq_dilithium"],
        "Sampling": ["poly_uniform_base_dilithium", "poly_uniform_gamma1_base_dilithium", "poly_challenge", "poly_chknorm_base_dilithium", "poly_uniform_eta_base_dilithium", "poly_uniform", "poly_uniform_eta", "poly_chknorm_dilithium", "poly_uniform_gamma1_dilithium"],
        "Rounding": ["decompose_base_dilithium", "decompose_unsigned_base_dilithium", "poly_make_hint_dilithium", "poly_decompose_dilithium", "poly_decompose_unsigned_dilithium", "poly_use_hint_dilithium", "poly_power2round_base_dilithium", "poly_power2round_dilithium", "decompose_dilithium"],
        "Packing": ["polyw1_pack_dilithium", "polyeta_unpack_base_dilithium", "polyvec_encode_h_dilithium", "polyz_pack_base_dilithium", "polyt0_unpack_base_dilithium", "polyz_unpack_base_dilithium", "polyt1_unpack_dilithium", "polyvec_decode_h_dilithium", "polyeta_pack_dilithium", "polyt0_pack_base_dilithium", "polyt1_pack_dilithium", "polyt0_pack_dilithium", "polyz_unpack_dilithium", "polyeta_unpack_dilithium", "polyz_pack_dilithium", "polyt0_unpack_dilithium"],
        "SHAKE": ["SHAKE", "keccak_send_message", "keccakf", "shake_out", "sha3_update", "sha3_init", "shake_xof", "sha3_final"],
        "Other": ["verify_plain_dilithium", "sign_plain_dilithium", "key_pair_plain_dilithium", "main", "sign_base_dilithium", "verify_base_dilithium", "key_pair_base_dilithium", "key_pair_dilithium", "verify_dilithium", "sign_dilithium"]
    }

    PARAM_MAP = {
        "dilithium2": "dilithiumlow",
        "dilithium3": "dilithiummid",
        "dilithium5": "dilithiumhigh"
    }
else:
    _GROUPING = {
        "Polynomial Arithmetic": ["poly_reduce", "ntt_kyber", "basemul_acc_kyber", "basemul_kyber", "poly_add", "intt_kyber", "poly_sub", "intt_base_kyber", "ntt_base_kyber", "basemul_acc_base_kyber", "basemul_base_kyber", "poly_add_base", "poly_sub_base", "poly_toplant"],
        "Reduction": ["poly_reduce32_pos_dilithium", "poly_reduce32_dilithium", "poly_reduce32_short_dilithium", "poly_caddq_base_dilithium", "poly_make_positive"],
        "Sampling": ["poly_gen_matrix_plain", "poly_gen_matrix", "cbd3", "poly_getnoise_eta_1", "cbd2", "poly_getnoise_eta_2", "poly_uniform", "poly_uniform_eta", "poly_gen_matrix_base", "poly_uniform_gamma1_dilithium"],
        "Rounding": ["decompose_base_dilithium", "poly_make_hint_dilithium", "poly_decompose_dilithium", "poly_decompose_unsigned_dilithium", "poly_use_hint_dilithium", "poly_power2round_base_dilithium", "poly_power2round_dilithium", "decompose_dilithium"],
        "Packing": ["poly_decompress", "polyvec_decompress", "poly_tobytes", "polyvec_compress", "poly_compress", "poly_frombytes", "pack_pk", "pack_sk", "poly_frommsg", "pack_ciphertext", "unpack_pk", "unpack_sk", "poly_tomsg", "unpack_ciphertext", "poly_tomsg_base", "poly_frommsg_base", "polyt0_pack_dilithium", "polyz_unpack_dilithium", "polyeta_unpack_dilithium", "polyz_pack_dilithium", "polyt0_unpack_dilithium"],
        "SHAKE": ["SHAKE", "keccak_send_message", "keccakf", "shake_out", "sha3_update", "sha3_init", "shake_xof", "sha3_final"],
        "Other": ["indcpa_dec_base", "indcpa_dec_base", "indcpa_enc_base", "indcpa_keypair_base", "indcpa_enc_plain", "indcpa_dec_plain", "indcpa_keypair_plain", "kem_sk", "indcpa_dec", "indcpa_enc", "indcpa_keypair", "main", "crypto_kem_keypair", "crypto_kem_enc", "crypto_kem_dec"],
    }

    PARAM_MAP = {
        "mlkem512": "mlkemlow",
        "mlkem768": "mlkemmid",
        "mlkem1024": "mlkemhigh"
    }

# "Transpose"
GROUPING = dict()
for k, v in _GROUPING.items():
    for vi in v:
        GROUPING[vi] = k

class Evaluation:
    def __init__(self, benchmark_ids: List, file_name: str = "dilithium_bench.db"):
        self.benchmark_ids = benchmark_ids
        self.iter_func_instr_to_perf = {}
        self.instr_hist_median = {}
        self.func_instr_hist = {}
        self.iter_func_to_perf = {}
        self.func_to_perf = {}
        self.iter_cycles = {}
        self.func_names = []
        self.func_calls = {}
        self.func_calls = defaultdict(lambda: [], self.func_calls)
        self.operation = ""

        with sqlite3.connect(file_name) as con:
            cur = con.cursor()

            # Check all data belongs to the same operation:
            query = f"SELECT operation FROM benchmark WHERE id IN ({','.join(['?']*len(benchmark_ids))})"
            res = cur.execute(query, benchmark_ids)
            operations = [r[0] for r in res.fetchall()]
            assert len(set(operations)) == 1
            self.operation = operations[0]
            if HIGHSPEED:
                self.operation = self.operation.replace("_bench", f"{highspeed_label}_bench")

            # Get cycles per iteration
            query = f"SELECT benchmark_iteration_id, cycles FROM cycles JOIN benchmark_iteration ON benchmark_iteration.id = cycles.benchmark_iteration_id WHERE benchmark_iteration.benchmark_id IN ({','.join(['?']*len(benchmark_ids))})"
            res = cur.execute(query, benchmark_ids)
            el = res.fetchone()
            while el is not None:
                self.iter_cycles[el[0]] = el[1]
                el = res.fetchone()

            query = f"SELECT benchmark_iteration_id, func_name, instr_name, instr_count, stall_count FROM func_instrs JOIN benchmark_iteration ON benchmark_iteration.id = func_instrs.benchmark_iteration_id WHERE benchmark_iteration.benchmark_id IN ({','.join(['?']*len(benchmark_ids))})"
            res = cur.execute(query, benchmark_ids)
            el = res.fetchone()
            while el is not None:
                if el[0] not in self.iter_func_instr_to_perf:
                    self.iter_func_instr_to_perf[el[0]] = {}
                if el[1] not in self.iter_func_instr_to_perf[el[0]]:
                    self.iter_func_instr_to_perf[el[0]][el[1]] = {}
                if el[2] not in self.iter_func_instr_to_perf[el[0]][el[1]]:
                    self.iter_func_instr_to_perf[el[0]][el[1]][el[2]] = {}
                self.iter_func_instr_to_perf[el[0]][el[1]][el[2]] = el[3:5]

                el = res.fetchone()

            # Initialize iter_func_to_perf
            for i, func_stats in self.iter_func_instr_to_perf.items():
                if i not in self.iter_func_to_perf:
                    self.iter_func_to_perf[i] = {}
                    self.iter_func_to_perf[i] = defaultdict(lambda: [0, 0], self.iter_func_to_perf[i])
                for func_name, instruction_data in func_stats.items():
                    # Treat the cycles for SHAKE as a special case
                    _instruction_data = dict(instruction_data)
                    # Reads/Writes from/to WSRs account to Keccak only for us
                    shake_cycles = _instruction_data.pop('bn.wsrr', None)
                    if shake_cycles is not None:
                        self.iter_func_to_perf[i]["SHAKE"] = list(map(add, self.iter_func_to_perf[i]["SHAKE"], shake_cycles))
                    shake_cycles = _instruction_data.pop('bn.wsrw', None)
                    if shake_cycles is not None:
                        self.iter_func_to_perf[i]["SHAKE"] = list(map(add, self.iter_func_to_perf[i]["SHAKE"], shake_cycles))
                    self.iter_func_to_perf[i][func_name] = [sum(x) for x in zip(*_instruction_data.values())]

            # Verify no cycle got lost
            for i, func_cycles in self.iter_func_to_perf.items():
                assert self.iter_cycles[i] == sum([sum(x) for x in zip(*func_cycles.values())])

            # Assume all function calls call the same function
            self.func_names = list(next(iter(self.iter_func_to_perf.values())).keys())

            # Get number of function calls total
            query = f"SELECT callee_func_name, call_count FROM func_calls JOIN benchmark_iteration ON benchmark_iteration.id = func_calls.benchmark_iteration_id WHERE benchmark_iteration.benchmark_id IN ({','.join(['?']*len(benchmark_ids))})"
            res = cur.execute(query, benchmark_ids)
            el = res.fetchone()
            while el is not None:
                if not el[0].startswith("_"):
                    self.func_calls[el[0]].append(el[1])
                el = res.fetchone()
            self.func_calls["SHAKE"] = [1]
            self.func_calls["main"] = [1]
            self.func_calls = dict(self.func_calls)

            # Instruction Histogram Median
            _instr_hist = {}
            _instr_hist = defaultdict(lambda: [], _instr_hist)
            for _, func_stats in self.iter_func_instr_to_perf.items():
                instr_count = {}
                instr_count = defaultdict(lambda: 0, instr_count)
                for _, instruction_data in func_stats.items():
                    for instr, instrcount_stalls in instruction_data.items():
                        instr_count[instr] += instrcount_stalls[0]
                for instr, instr_count in instr_count.items():
                    _instr_hist[instr].append(instr_count)

            for instr, instr_counts in _instr_hist.items():
                self.instr_hist_median[instr] = round(median(instr_counts))

            self.instr_hist_median = dict(sorted(self.instr_hist_median.items(), key=lambda item: item[1], 
reverse=True))

    def cycles(self, stat_func):
        return round(stat_func(self.iter_cycles.values()))

    def per_func_stat(self, stat_func, per_call=False):
        # Initialize func_to_perf
        # usually, no division
        div = 1
        per_func_stat = {}
        per_func_stat = defaultdict(lambda: [], per_func_stat)
        # collect data
        for i, func_stats in self.iter_func_to_perf.items():
            for func_name, cycles in func_stats.items():
                per_func_stat[func_name].append(cycles)
        # compute statistics
        for func_name, cycles in per_func_stat.items():
            if per_call and func_name not in ["main", "SHAKE"]:
                div = mean(self.func_calls[func_name])
            per_func_stat[func_name] = [stat_func([c[j]/div for c in per_func_stat[func_name]]) for j in range(2)]
        return dict(per_func_stat)

STAT_FUNC = median

def main():
    parser = argparse.ArgumentParser(description='Evaluate Benchmark Database.')
    parser.add_argument('-f', '--filename' , help="<Required> Define the database filename.", required=True)
    parser.add_argument('-o', '--output' , help="<Optional> Define the output file. Default: eval_result.txt", nargs='?', const="eval_result.txt")
    parser.add_argument('-i','--ids', nargs='+', help='<Required> ids of entries from the database to evaluate, space separated.', type=int, required=True)
    
    args = parser.parse_args()
    with open(args.output, "w") as outfile:
        for dben in args.ids:
            e = Evaluation([dben], file_name=args.filename)
            outfile.write(f" --- {e.operation}: index {dben} in {args.filename} ---\n")

            per_func_stat = e.per_func_stat(lambda x: round(STAT_FUNC(x)), per_call=False)
            # sort
            per_func_stat = dict(sorted(per_func_stat.items(), key=lambda item: sum(item[1]), reverse=True))
            per_group_data = {}
            per_group_data = defaultdict(lambda: [0, 0], per_group_data)

            for k, v in per_func_stat.items():
                per_group_data[GROUPING[k]] = list(map(add, per_group_data[GROUPING[k]], v))
            per_group_data = dict(sorted(per_group_data.items(), key=lambda item: sum(item[1]), reverse=True))

            total_pie = sum([sum(v) for _, v in per_group_data.items()])

            outfile.write("\nOverall Stats\n")
            headers = ["Metric", "Cycles"]
            cycle_data = [["Mean", e.cycles(mean)], ["Median", e.cycles(median)], ["Std. Dev.", e.cycles(stdev)]]
            outfile.write(tabulate(cycle_data, headers) + "\n")

            outfile.write("\nGroup Percentages\n")
            headers = ["Group", "Percentage"]
            pie_data = [[k, round(sum(v)/total_pie*100)] for k, v in per_group_data.items() if round(sum(v)/total_pie*100) != 0]
            outfile.write(tabulate(pie_data, headers) + "\n")

            outfile.write("\nPer Function Statistics (accumulated)\n")
            headers = ["Function", "Calls", "Instructions", "Stall", "Total", "Per Call"]
            per_func_acc_data = [[k, round(STAT_FUNC(e.func_calls[k])), v[0], v[1], sum(v), round(sum(v)/round(STAT_FUNC(e.func_calls[k])))] for k, v in per_func_stat.items()]
            outfile.write(tabulate(per_func_acc_data, headers) + "\n")

            outfile.write("\nInstruction Histogram\n")
            headers = ["Instruction", "Count"]
            instr_hist_data = [[k, v] for k, v in e.instr_hist_median.items()]
            outfile.write(tabulate(instr_hist_data, headers) + "\n\n\n")

if __name__ == '__main__':
    main()