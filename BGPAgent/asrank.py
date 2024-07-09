import argparse
import os
import bz2
import re
from collections import defaultdict
from graph import Graph

def custcone(a, b):
    if b not in data[a]['cone']:
        data[a]['cone'][b] += 1
        for c in data[b]['cone']:
            data[a]['cone'][c] += data[b]['cone'][c]
        if 'provs' in data[a]:
            for p in data[a]['provs']:
                custcone(p, b)

def r(a, b, rel):
    if b in r_data[a]:
        raise ValueError(f"Fatal: a relationship already exists for {a} + {b}")
    if verbose:
        print(f"# {a}/{b}/{rel}")
    if rel == -1:  # p2c
        data[b]['provs'][a] = 1
        data[a]['custs'][b] = 1
        custcone(a, b)
    elif rel == 0:  # p2p
        data[b]['peers'][a] = 1
        data[a]['peers'][b] = 1
    elif rel == 2:  # s2s
        data[a]['sibls'][b] = 1
        data[b]['sibls'][a] = 1
    r_data[a][b] = rel
    r_data[b][a] = 1 if rel == -1 else rel

def clique(asn):
    return asn in clique_data

def p2c_ok(x, y):
    if clique(y):
        return False
    if 'cone' not in data[y]:
        return True
    return x not in data[y]['cone']

def c2p(x, y):
    return r_data.get(x, {}).get(y) == 1

def p2p(x, y):
    return r_data.get(x, {}).get(y) == 0

def p2c(x, y):
    return r_data.get(x, {}).get(y) == -1

def global_degree(asn):
    return len(data[asn]['links']) if 'links' in data[asn] else 0

def transit_degree(asn):
    return len(data[asn]['trans']) if 'trans' in data[asn] else 0

def provider_degree(asn):
    return len(data[asn]['provs']) if 'provs' in data[asn] else 0

def peer_degree(asn):
    return len(data[asn]['peers']) if 'peers' in data[asn] else 0

def link_degree(a, b):
    if 'trips' in data[a] and b in data[a]['trips']:
        return len(data[a]['trips'][b])
    return 0

def trip_sum(x, y, z):
    if 'quads' in data[x] and y in data[x]['quads'] and z in data[x]['quads'][y]:
        return sum(data[x]['quads'][y][z].values())
    return 0

def trip_degree(x, y, z):
    if 'quads' in data[x] and y in data[x]['quads'] and z in data[x]['quads'][y]:
        return len(data[x]['quads'][y][z])
    return 0

def trip_z(x, y, z):
    if 'trip_z' in data[x] and y in data[x]['trip_z'] and z in data[x]['trip_z'][y]:
        return data[x]['trip_z'][y][z]
    return 0

def upstr_c(x, y, z):
    if 'upstr' in data[x] and y in data[x]['upstr'] and z in data[x]['upstr'][y]:
        return data[x]['upstr'][y][z]
    return 0

def trips_c(x, y, z):
    if 'trips' in data[x] and y in data[x]['trips'] and z in data[x]['trips'][y]:
        return data[x]['trips'][y][z]
    return 0

def peerrank(a, b, x):
    i, j = link_degree(x, a), link_degree(x, b)
    if i > j:
        return -1
    if i < j:
        return 1
    i, j = link_degree(a, x), link_degree(b, x)
    if i < j:
        return -1
    if i > j:
        return 1
    i, j = transit_degree(a), transit_degree(b)
    if i > j:
        return -1
    if i < j:
        return 1
    i, j = global_degree(a), global_degree(b)
    if i > j:
        return -1
    if i < j:
        return 1
    return 0

def top_down(a, b):
    at, bt = transit_degree(a), transit_degree(b)
    ag, bg = global_degree(a), global_degree(b)
    if clique(a):
        ac = 1
    else:
        ac = 0
    if clique(b):
        bc = 1
    else:
        bc = 0
    if ac or bc:
        if ac > bc:
            return -1
        if ac < bc:
            return 1
    if at > bt:
        return -1
    if at < bt:
        return 1
    if ag > bg:
        return -1
    if ag < bg:
        return 1
    if a < b:
        return -1
    if a > b:
        return 1
    return 0

def parse_path(path):
    if path.startswith('#') or '||' in path:
        return []
    path_parts = path.split('|')
    if filtered_flag:
        return path_parts
    if path_parts[0] in exclvps:
        return []
    ases = {}
    clique_flag = 0
    np = []
    for i, asn in enumerate(path_parts):
        asn = int(asn)
        if (asn == 0 or asn == 23456 or asn >= 394240 or
                61440 <= asn <= 131071 or 133120 <= asn <= 196607 or
                199680 <= asn <= 262143 or 263168 <= asn <= 327679 or
                328704 <= asn <= 393215):
            return []
        if asn in ixp:
            continue
        if asn in ases:
            return []
        ases[asn] = 1
        np.append(asn)
        if clique(asn):
            if clique_flag != 0 and not clique(path_parts[i - 1]):
                return []
            clique_flag = 1
    return np

def read_paths():
    global data, vpoc
    data, vpoc = defaultdict(lambda: defaultdict(lambda: defaultdict(int))), defaultdict(lambda: defaultdict(int))
    open_func = bz2.open if paths.endswith('.bz2') else open
    with open_func(paths, 'rt') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                if pass_num == 0:
                    print(line)
                if re.match(r'^# inferred clique: (.+)$', line):
                    for asn in line.split()[3:]:
                        clique_data[int(asn)] = 1
                continue
            path_parts = parse_path(line)
            if not path_parts:
                continue
            vpoc[path_parts[0]][path_parts[-1]] += 1
            if len(path_parts) == 3:
                data[path_parts[0]]['vp'][path_parts[1]][path_parts[2]] += 1
            for i in range(1, len(path_parts)):
                a, x = path_parts[i - 1], path_parts[i]
                data[a]['links'][x] += 1
                data[x]['links'][a] += 1
                if i < len(path_parts) - 1:
                    b = path_parts[i + 1]
                    data[b]['links'][x] += 1
                    data[x]['links'][b] += 1
                    data[x]['trans'][a] += 1
                    data[x]['trans'][b] += 1
                    data[a]['trips'][x][b] += 1
                    data[b]['trips'][x][a] += 1
                    data[b]['upstr'][x][a] += 1
                    data[x]['povup'][a][b] += 1
                    if i + 1 < len(path_parts) - 1:
                        c = path_parts[i + 2]
                        data[a]['quads'][x][b][c] += 1
                    else:
                        data[a]['trip_z'][x][b] += 1

def rank_peers():
    for asn in data:
        ranking = sorted(data[asn]['links'], key=lambda y: peerrank(asn, y, asn))
        data[asn]['ranking'] = ranking
        for i, x in enumerate(ranking):
            data[asn]['rank'][x] = i + 1

def select_providers(x):
    if clique(x):
        return
    for y in sorted(data[x]['links'], key=lambda y: top_down(x, y)):
        if y in r_data[x]:
            continue
        r_val = 0
        if r_val == 0 and provider_degree(y) > 0:
            for z in data[y]['provs']:
                if upstr_c(x, y, z) > 0:
                    r_val = -1
                    break
        if r_val == 0 and peer_degree(y) > 0:
            for z in data[y]['peers']:
                if upstr_c(x, y, z) > 0 or trips_c(x, y, z) > 2:
                    r_val = -1
                    break
        if r_val == -1 and p2c_ok(y, x):
            r(y, x, r_val)

def provider_to_larger_customer():
    xyz = {}
    for x in data:
        if 'trips' not in data[x]:
            continue
        for y in data[x]['trips']:
            if r_data.get(x, {}).get(y) != -1:
                continue
            for z in data[x]['trips'][y]:
                if y in r_data or upstr_c(z, y, x) == 0 or trip_z(x, y, z) == 0 or transit_degree(y) > transit_degree(z):
                    continue
                xyz[f"{x}:{y}:{z}"] = data[x]['trips'][y][z]
    while xyz:
        xyz_items = sorted(xyz.items(), key=lambda item: item[1], reverse=True)
        xyz_key, freq = xyz_items[0]
        x, y, z = map(int, xyz_key.split(':'))
        del xyz[xyz_key]
        if freq < 3 or y in r_data or not p2c_ok(y, z):
            continue
        r(y, z, -1)
        for zz in data[z]['links']:
            if zz in r_data or upstr_c(zz, z, y) == 0:
                continue
            if transit_degree(zz) > transit_degree(z):
                xyz[f"{y}:{z}:{zz}"] = data[y]['trips'][z][zz]
            elif p2c_ok(z, zz):
                r(z, zz, -1)

def provider_less_network(x):
    for y in sorted(data[x]['links'], key=lambda y: top_down(x, y)):
        if link_degree(y, x) == 0 or y in r_data:
            continue
        r(x, y, 0)
        for z in data[y]['trips'][x]:
            if z in r_data or not p2c_ok(x, z):
                continue
            r(x, z, -1)
            for zz in data[z]['links']:
                if zz in r_data or upstr_c(zz, z, x) == 0 or transit_degree(zz) >= transit_degree(z):
                    continue
                if p2c_ok(z, zz):
                    r(z, zz, -1)

def fold_p2p(x):
    if transit_degree(x) == 0:
        return
    p2p_dict = defaultdict(dict)
    for y in data[x]['povup']:
        if x in r_data and r_data[x][y] != 0:
            continue
        if provider_degree(x) > 0:
            skip = False
            for z in data[x]['provs']:
                if trips_c(y, x, z) > 0:
                    skip = True
                    break
            if skip:
                continue
        for z in data[x]['povup'][y]:
            if z not in r_data:
                p2p_dict[y][z] = 1
    if not p2p_dict:
        return
    rhs = defaultdict(int)
    for y in p2p_dict:
        for z in p2p_dict[y]:
            rhs[z] += 1
    for y in list(p2p_dict.keys()):
        if y in rhs:
            del p2p_dict[y]
            for z in list(p2p_dict.keys()):
                if y in p2p_dict[z]:
                    del p2p_dict[z][y]
    rhs.clear()
    for y in p2p_dict:
        for z in p2p_dict[y]:
            rhs[z] += 1
    for y in sorted(rhs, key=rhs.get, reverse=True):
        if transit_degree(x) < transit_degree(y) or not p2c_ok(x, y) or y in r_data:
            continue
        r(x, y, -1)
        for z in data[y]['povup'][x]:
            if z in r_data or transit_degree(y) < transit_degree(z) or not p2c_ok(y, z):
                continue
            r(y, z, -1)

def td_sum(*asns):
    return sum(transit_degree(asn) for asn in asns)

def td_asn(asn):
    if asn not in data:
        return f"{asn}:?"
    return f"{asn}:{transit_degree(asn)}"

def clique_link_hash(h, y, x):
    if x not in data or y not in data[x]['links']:
        return False
    trip = False
    for z in h:
        if z in {y, x}:
            continue
        if upstr_c(x, y, z) > 0:
            td = trip_degree(z, y, x)
            tz = trip_z(z, y, x)
            if verbose and opt == 'clique':
                print(f"# tripdeg {x}: {z}|{y}|{x} {td} {tz} {upstr_c(x, y, z)}:{trip_sum(z, y, x)}")
            if td <= 5 and tz == 0 and upstr_c(x, y, z) == trip_sum(z, y, x):
                continue
            if td > 2:
                trip = True
    return not trip

def clique_link_array(a, z, x):
    if x not in data or z not in data[x]['links']:
        return False
    trip = False
    for y in a:
        if y in {z, x}:
            continue
        if upstr_c(x, y, z) > 0:
            td = trip_degree(z, y, x)
            tz = trip_z(z, y, x)
            if verbose and opt == 'clique':
                print(f"# tripdeg {x}: {z}|{y}|{x} {td} {tz} {upstr_c(x, y, z)}:{trip_sum(z, y, x)}")
            if td <= 5 and tz == 0 and upstr_c(x, y, z) == trip_sum(z, y, x):
                continue
            if td > 2:
                trip = True
    return not trip

def python_clique(*ases):
    if verbose and opt == 'clique':
        print(f"# pyth: {' '.join(map(str, ases))}")
        for asn in ases:
            print(f"#  {td_asn(asn)}")
    g = Graph()
    for asn in ases:
        g.add_node(asn)
    for i, x in enumerate(ases):
        for y in ases[i + 1:]:
            if clique_link_array(ases, x, y) and clique_link_array(ases, y, x):
                g.add_edge(x, y)
    cliques = g.find_all_cliques()
    cs = {tuple(sorted(clique)): td_sum(*clique) for clique in cliques}
    sorted_cs = sorted(cs.items(), key=lambda item: item[1], reverse=True)
    if verbose and opt == 'clique':
        for clique, td in sorted_cs:
            print(f"# pytx: {' '.join(map(str, clique))} ({td})")
    return sorted_cs[0][0] if sorted_cs else []

def infer_clique(N):
    rank = sorted(data, key=top_down)
    c1 = {}
    b = {}
    i = -1
    while i <= len(rank):
        if i == -1:
            N_ases = [rank[j] for j in range(N) if rank[j] not in b]
            N_clique = python_clique(*N_ases)
            if not N_clique:
                return []
            c1 = {asn: 0 for asn in N_clique}
            if verbose:
                print(f"#  raw: {' '.join(map(str, sorted(c1)))}")
                for x in c1:
                    for y in c1:
                        if x != y:
                            for z in c1:
                                if x != z and y != z and upstr_c(x, y, z):
                                    print(f"# tripraw: {z}|{y}|{x} {trip_degree(z, y, x)}")
            i = N
            continue
        x = rank[i]
        if x in c1 or x in b:
            i += 1
            continue
        if global_degree(x) < len(c1):
            break
        miss = [y for y in c1 if not clique_link_hash(c1, y, x)]
        if miss:
            if verbose:
                print(f"# missing-{len(miss)} {x}: {' '.join(map(str, sorted(miss)))}")
            i += 1
            continue
        c1[x] = i
        if verbose:
            print(f"#  add {td_asn(x)}: {' '.join(map(str, sorted(c1)))}")
        i += 1
    if verbose:
        print(f"# c1: {' '.join(map(str, sorted(c1)))}")
    return python_clique(*(list(c1) + list(b)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AS Rank Script')
    parser.add_argument('--ixp', type=str, help='IXP ASes')
    parser.add_argument('--clique', type=str, help='Clique ASes')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--exclvps', type=str, help='Excluded VPs')
    parser.add_argument('--filtered', action='store_true', help='Filtered flag')
    parser.add_argument('paths', type=str, help='Paths file')
    parser.add_argument('opt', type=str, nargs='?', default='rels', help='Optional argument')
    args = parser.parse_args()

    ixp_string = args.ixp
    clique_string = args.clique
    verbose = args.verbose
    exclvps_string = args.exclvps
    filtered_flag = args.filtered
    paths = args.paths
    opt = args.opt

    ixp = {int(asn): 1 for asn in ixp_string.split()} if ixp_string else {}
    exclvps = {int(asn): 1 for asn in exclvps_string.split()} if exclvps_string else {}
    clique_data = {int(asn): 1 for asn in clique_string.split()} if clique_string else {}
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    vpoc = defaultdict(lambda: defaultdict(int))
    r_data = defaultdict(dict)
    pass_num = 0

    if opt == "clique":
        read_paths()
        clique = infer_clique(10)
        print(f"# inferred clique: {' '.join(map(str, sorted(clique)))}")
    elif opt == "table-transit-raw":
        read_paths()
        print("# ASN transit global")
        for asn in sorted(data, key=top_down):
            print(f"{asn} {transit_degree(asn)} {global_degree(asn)}")
    else:
        if not clique_string and not filtered_flag:
            read_paths()
            clique = infer_clique(10)
            clique_data.update({asn: 1 for asn in clique})
            print(f"# inferred clique: {' '.join(map(str, sorted(clique)))}")
            if ixp:
                print(f"# IXP ASes: {' '.join(map(str, sorted(ixp)))}")
            if exclvps:
                print(f"# Excluded VPs: {' '.join(map(str, sorted(exclvps)))}")
        if opt in ["filtered-paths", "filtered-out"]:
            open_func = bz2.open if paths.endswith('.bz2') else open
            with open_func(paths, 'rt') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#'):
                        continue
                    path_parts = parse_path(line)
                    if not path_parts and opt == "filtered-out":
                        print(line)
                    elif path_parts and opt == "filtered-paths":
                        print('|'.join(map(str, path_parts)))
        else:
            read_paths()
            if opt == "rels":
                step = 1
                if verbose:
                    print(f"# step {step}: set peering in clique")
                for x in sorted(clique_data):
                    for y in sorted(clique_data):
                        if x < y:
                            r(x, y, 0)
                step += 1
                if verbose:
                    print(f"# step {step}: initial provider assignment")
                for asn in sorted(data, key=top_down):
                    select_providers(asn)
                step += 1
                if verbose:
                    print(f"# step {step}: providers for stub ASes #1")
                for x in vpoc:
                    if len(vpoc[x]) * 50 > len(data):
                        continue
                    for y in data[x]['vp']:
                        for z in data[x]['vp'][y]:
                            if y not in r_data and transit_degree(z) == 0:
                                r(y, z, -1)
                step += 1
                if verbose:
                    print(f"# step {step}: provider to larger customer")
                provider_to_larger_customer()
                step += 1
                if verbose:
                    print(f"# step {step}: provider-less networks")
                for x in sorted(data, key=top_down):
                    if provider_degree(x) > 0 or clique(x):
                        continue
                    if transit_degree(x) < 10:
                        continue
                    provider_less_network(x)
                step += 1
                if verbose:
                    print(f"# step {step}: c2p for stub-clique relationships")
                for x in clique_data:
                    for y in data[x]['links']:
                        if transit_degree(y) == 0 and y not in r_data:
                            r(x, y, -1)
                step += 1
                if verbose:
                    print(f"# step {step}: fold p2p links")
                for asn in sorted(data, key=top_down):
                    fold_p2p(asn)
                step += 1
                if verbose:
                    print(f"# step {step}: everything else is p2p")
                for x in data:
                    for y in data[x]['links']:
                        if y not in r_data:
                            r(x, y, 0)
                for x in sorted(r_data):
                    for y in sorted(r_data[x]):
                        if r_data[x][y] == 1:
                            continue
                        if r_data[x][y] == 0 and x > y:
                            continue
                        print(f"{x}|{y}|{r_data[x][y]}")
            elif opt == "table-transit":
                print("# ASN transit global")
                for x in sorted(data, key=lambda x: transit_degree(x), reverse=True):
                    print(f"{x} {transit_degree(x)} {global_degree(x)}")
            elif opt == "table-topdown":
                print("# ASN transit global")
                for x in sorted(data, key=top_down):
                    print(f"{x} {transit_degree(x)} {global_degree(x)}")
            elif opt == "table-rank":
                rank_peers()
                for x in sorted(data):
                    for y in data[x]['ranking']:
                        print(f"{x} {y} {global_degree(y)} {transit_degree(y)} {link_degree(x, y)} {link_degree(y, x)} {data[y]['rank'][x]}/{global_degree(y)}")
            elif opt == "table-rank2":
                rank_peers()
                print("# from to from-local to-local from-rank to-rank")
                for x in sorted(data):
                    for y in sorted(data[x]['links']):
                        if x > y:
                            continue
                        print(f"{x} {y} {link_degree(x, y)} {link_degree(y, x)} {data[x]['rank'][y]}/{global_degree(x)} {data[y]['rank'][x]}/{global_degree(y)}")
