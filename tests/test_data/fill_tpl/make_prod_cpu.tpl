#  TODO: the following line should generate this ini file
;namd_scripts --type cpu --run {run} --name test --input_name 7.1 --first {first}
# cpu = production_cpu_pbs.tpl
# run = integer,tpl value
# input = input_name, tpl value
# first = first, tpl value
[main]
tpl_file = tests/test_data/fill_tpl/production_cpu_pbs.tpl, tests/test_data/fill_tpl/production_gpu_inp.tpl
filled_tpl_name = {name}.pbs, {name}.inp
out_dir = tests/test_data/fill_tpl/
# Important Notes for this configuration file:
# 1) a [main] section is required
# 2) optional sections are [tpl_vals] and [tpl_val_equations]
# 3) [tpl_val_equations] allows key values to be calculated based on other key values. Equations are evaluated in the
#    order provided, so if an equation depends on the value computed from another equation, list the dependent
#    equation after its inputs.
# 4) Multiple values and equations may be listed for any keys. In that case, the program will create multiple output
#    files. If a static 'filled_tpl_name' is provided, the file will be overwritten, leaving only one filled file at
#    the end. The 'filled_tpl_name' can include keys (i.e. filled_tpl_name = {{key1}}.txt), so if multiple values are
#    listed for key1 (i.e. key1 = A,B,C), multiple output files will be created (A.txt, B.txt, C.txt)."
[tpl_vals]
name = test
run = 500000
first = 500000
structure = test.psf
coordinates = test.pdb
input_name = 7.1
output_name = test
[tpl_equations]
walltime = int({run}/500000*15)
last = {first}+{run}
