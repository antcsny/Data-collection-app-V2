from kuka import KUKA_Trace, KUKA_Handler

h = KUKA_Handler("192.168.1.153", 7000)
trace = KUKA_Trace(h)

trace.name = "2024-05-27_16-06-53[70]_R2"

pairs = trace.find_pairs(trace.name)

dats = []

for pair in pairs:

    dat_path = trace.temp_folder.joinpath(trace.name).joinpath(pair[0])
    dat = trace.read_dat(dat_path)

    dats.append(dat)

min_sampling = 1
for dat in dats:
    min_sampling = min(min_sampling, dat.sampling)

min_len = 1e9
for dat in dats:
    ratio = int(dat.sampling // min_sampling)
    min_len = min(min_len, dat.length * ratio)

print(min_len)