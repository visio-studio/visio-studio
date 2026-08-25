#!/usr/bin/env python3
"""Estrae da un .glb la geometria pezzo per pezzo e la salva in un JSON compatto
per il renderer WebGL del sito (nessuna libreria, ne in Python ne nel browser).

    python3 strumenti/glb-a-json.py modelli/madia.glb madia-3d.json

Il modello va esportato MONTATO, con un gruppo per pezzo e nomi parlanti:
le posizioni di partenza dell'animazione sono calcolate nel sito a partire
dal nome e dalla posizione del pezzo, non dal file.
"""
import json, struct, sys, os

def carica(path):
    d = open(path, 'rb').read()
    off, g, BIN = 12, None, None
    while off < len(d):
        clen, ctype = struct.unpack('<II', d[off:off+8])
        ch = d[off+8:off+8+clen]
        if   ctype == 0x4E4F534A: g = json.loads(ch)
        elif ctype == 0x004E4942: BIN = ch
        off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
    return g, BIN

CT = {5120:('b',1), 5121:('B',1), 5122:('h',2), 5123:('H',2), 5125:('I',4), 5126:('f',4)}
NC = {"SCALAR":1, "VEC2":2, "VEC3":3, "VEC4":4}

def leggi(g, BIN, ai):
    a = g["accessors"][ai]; bv = g["bufferViews"][a["bufferView"]]
    fmt, sz = CT[a["componentType"]]; nc = NC[a["type"]]
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or sz * nc
    return [struct.unpack_from('<' + fmt * nc, BIN, base + i * stride) for i in range(a["count"])]

def mul(a, b):
    return [sum(a[i*4+k] * b[k*4+j] for k in range(4)) for i in range(4) for j in range(4)]

def trs(n):
    if "matrix" in n:
        m = n["matrix"]; return [m[j*4+i] for i in range(4) for j in range(4)]
    t = n.get("translation", [0,0,0]); x,y,z,w = n.get("rotation", [0,0,0,1]); s = n.get("scale", [1,1,1])
    R = [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w), 0,
         2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w), 0,
         2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y), 0, 0,0,0,1]
    M = mul(R, [s[0],0,0,0, 0,s[1],0,0, 0,0,s[2],0, 0,0,0,1])
    M[3], M[7], M[11] = t; M[15] = 1
    return M

def gruppo(n):
    n = n.lower()
    if "marmo" in n: return "marmo"
    if "pied" in n or "zoccolo" in n: return "base"
    if "anta" in n: return "anta"
    return "corpo"

def estrai(src, dst):
    g, BIN = carica(src)
    N = g["nodes"]; parts = []
    def walk(i, P, nome):
        n = N[i]; M = mul(P, trs(n)); nm = n.get("name", "")
        if nm and not nm.startswith("3DGeom"): nome = nm
        # 'Active View' e la camera che SimLab aggiunge all'export: da scartare
        if "mesh" in n and nome and "Active View" not in nome:
            for pr in g["meshes"][n["mesh"]].get("primitives", []):
                pos = leggi(g, BIN, pr["attributes"]["POSITION"])
                nor = leggi(g, BIN, pr["attributes"]["NORMAL"]) if "NORMAL" in pr["attributes"] else []
                idx = [v[0] for v in leggi(g, BIN, pr["indices"])] if "indices" in pr else list(range(len(pos)))
                V = [[M[0]*p[0]+M[1]*p[1]+M[2]*p[2]+M[3],
                      M[4]*p[0]+M[5]*p[1]+M[6]*p[2]+M[7],
                      M[8]*p[0]+M[9]*p[1]+M[10]*p[2]+M[11]] for p in pos]
                NR = []
                for q in nor:
                    v = [M[0]*q[0]+M[1]*q[1]+M[2]*q[2], M[4]*q[0]+M[5]*q[1]+M[6]*q[2], M[8]*q[0]+M[9]*q[1]+M[10]*q[2]]
                    l = (v[0]**2 + v[1]**2 + v[2]**2) ** .5 or 1
                    NR.append([c/l for c in v])
                parts.append({"n": nome, "V": V, "NR": NR, "I": idx})
        for c in n.get("children", []): walk(c, M, nome)
    for sc in g["scenes"]:
        for r in sc["nodes"]: walk(r, [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1], "")
    if not parts: sys.exit("nessuna geometria trovata in " + src)

    mn = [1e18]*3; mx = [-1e18]*3
    for p in parts:
        for v in p["V"]:
            for k in range(3): mn[k] = min(mn[k], v[k]); mx[k] = max(mx[k], v[k])
    # ricentrato in X/Z, appoggiato a Y=0
    cx = (mn[0]+mx[0])/2; cz = (mn[2]+mx[2])/2; by = mn[1]
    out = {"dim": [round(mx[k]-mn[k], 4) for k in range(3)], "parts": []}
    for p in parts:
        v = []
        for a in p["V"]: v += [round(a[0]-cx, 4), round(a[1]-by, 4), round(a[2]-cz, 4)]
        nr = []
        for a in p["NR"]: nr += [round(c, 3) for c in a]
        out["parts"].append({"n": p["n"], "g": gruppo(p["n"]),
                             "cx": round(sum(v[0::3]) / (len(v)//3), 4), "v": v, "nr": nr, "i": p["I"]})
    out["parts"].sort(key=lambda p: (p["g"], p["cx"]))
    json.dump(out, open(dst, "w"), separators=(",", ":"))
    print("%s -> %s  (%d pezzi, %.1f KB, ingombro %s m)" %
          (src, dst, len(out["parts"]), os.path.getsize(dst)/1024, out["dim"]))

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    estrai(sys.argv[1], sys.argv[2])
